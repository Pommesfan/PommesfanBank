import traceback
from Server.Sessions import CardTerminalSession
from Utils import *
from BankService import BankService


class PaymentOrder:
    def __init__(self, card_number, card_key, amount, reference, transfer_code):
        self.card_number = card_number
        self.card_key = card_key
        self.amount = amount
        self.reference = reference
        self.transfer_code = transfer_code
        self.last_nack = -1


class CardTerminalService(BankService):
    def __init__(self, db_interface, transfer_function, udp_socket, read_lock, write_lock, session_list,
                 ongoing_session_list,
                 CURRENCY_B, DECIMAL_PLACE_B):
        super().__init__(db_interface, transfer_function, udp_socket, session_list, ongoing_session_list,
                         CURRENCY_B, DECIMAL_PLACE_B, read_lock, write_lock, self.card_terminal_routine)

    def __start_login(self, paket, src):
        def query_function(terminal_id):
            res = self._db_interface.query_terminal(terminal_id)
            if res is None:
                print("Terminal '" + terminal_id + "' nicht registriert")
                return None
            else:
                terminal_key_b = res[1].encode(UTF8STR)
                return terminal_id, terminal_key_b

        self.start_login(paket, src, query_function, CardTerminalSession)

    def __complete_login(self, paket, src):
        def query_function(terminal_id):
            res = self._db_interface.query_terminal(terminal_id)
            terminal_key_b = res[1].encode(UTF8STR)
            return res, terminal_id, terminal_key_b

        def message_function(user_id, query_res, success):
            msg = "Login Terminal: '" + user_id
            if success:
                msg += "' erfolgreich"
            else:
                msg += "' nicht erfolgreich"
            print(msg)

        self.complete_login(paket, src, query_function, message_function)

    def __init_payment(self, session, s):
        session.order_lock.acquire()
        card_number = s.get_slice(16)
        card_key = s.get_slice(64)
        amount = s.get_int()
        reference = s.next_slice().decode(UTF8STR)
        transfer_code = create_alpha_numeric(8)
        session.current_order = PaymentOrder(card_number, card_key, amount, reference, transfer_code)
        answer_paket = int_to_bytes(PAYMENT_ORDER_ACK) + transfer_code.encode(UTF8STR)
        self.answer_to_client(session, answer_paket)
        session.order_lock.release()

    def __execute_payment(self, session, s):
        session.order_lock.acquire()
        order = session.current_order
        transfer_code = s.get_slice(8).decode(UTF8STR)

        def on_not_execute(nack):
            answer_paket = int_to_bytes(nack) + transfer_code.encode(UTF8STR)
            self.answer_to_client(session, answer_paket)
            session.order_lock.release()

        if not order or order.transfer_code != transfer_code:
            on_not_execute(PAYMENT_EXECUTE_NACK_TRANSFER_CODE)
            print("Transfer code nicht erfasst")
            return

        terminal = self._db_interface.query_terminal(session.user_id)
        account_to = terminal[2]

        res = self._db_interface.query_account_to_card(order.card_number.decode(UTF8STR))
        if not res:
            order.last_nack = PAYMENT_EXECUTE_NACK_CARDNUMBER
            on_not_execute(PAYMENT_EXECUTE_NACK_CARDNUMBER)
            print("Karte nicht registriert")
            return

        account_from = res[0]
        card_key_from_db = res[1]

        if card_key_from_db != order.card_key:
            order.last_nack = PAYMENT_EXECUTE_NACK_CARDKEY
            on_not_execute(PAYMENT_EXECUTE_NACK_CARDKEY)
            print("Kartenzahlung nicht erfolgreich")
            return

        transfer_id = self._transfer_function(DEBIT_CARD_PAYMENT, account_from, account_to, order.amount,
                                              order.reference,
                                              query_autoincrement_id=True)
        self._db_interface.acquire_lock()
        self._db_interface.create_card_payment(transfer_id, order.card_number, transfer_code)
        self._db_interface.release_lock()
        session.current_order = None
        answer_paket = int_to_bytes(PAYMENT_EXECUTE_ACK) + order.transfer_code.encode(UTF8STR)
        self.answer_to_client(session, answer_paket)
        session.order_lock.release()

    def __proof_payment(self, session, s):
        session.order_lock.acquire()
        transfer_code = s.get_slice(8).decode(UTF8STR)
        current_order = session.current_order
        if current_order and session.current_order.transfer_code == transfer_code and current_order.last_nack != -1:
            self.answer_to_client(session, int_to_bytes(current_order.last_nack))
        else:
            self._db_interface.acquire_lock()
            res = self._db_interface.query_card_payment(transfer_code)
            self._db_interface.release_lock()

            if res:
                answer_paket = int_to_bytes(PAYMENT_PROOF_ACK) + transfer_code.encode(UTF8STR)
            else:
                answer_paket = int_to_bytes(PAYMENT_PROOF_NACK)
            self.answer_to_client(session, answer_paket)
        session.order_lock.release()

    def logout(self, session):
        if self._session_list.remove_session(session.session_id) == -1:
            self.error("remove session: session_id not found")
        else:
            print("Terminal: " + session.user_id + " ausgeloggt")

    def card_terminal_routine(self):
        while True:
            try:
                self._read_lock.acquire()
                paket, src = self._udp_socket.recvfrom(1024)
                self._read_lock.release()
                s = SliceIterator(paket)
                command = s.get_int()
                if command == START_LOGIN:
                    self.__start_login(s, src)
                elif command == COMPLETE_LOGIN:
                    self.__complete_login(s, src)
                elif command == CARD_PAYMENT_COMMAND:
                    session: CardTerminalSession = self._session_list.get_session_from_id(s.get_slice(8), src)
                    paket = session.aes_d.decrypt(s.get_last_slice())
                    s = SliceIterator(paket)
                    payment_cmd = s.get_int()
                    if payment_cmd == INIT_CARD_PAYMENT_COMMAND:
                        self.__init_payment(session, s)
                    elif payment_cmd == EXECUTE_CARD_PAYMENT_COMMAND:
                        self.__execute_payment(session, s)
                    elif payment_cmd == PROOF_CARD_PAYMENT_COMMAND:
                        self.__proof_payment(session, s)
                    elif payment_cmd == EXIT_COMMAND:
                        self.logout(session)
            except:
                traceback.print_exc()
