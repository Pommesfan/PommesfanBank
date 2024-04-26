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
                return None, None
            else:
                terminal_key_b = res[1].encode(UTF8STR)
                return terminal_id, terminal_key_b

        self.start_login(paket, src, query_function, CardTerminalSession)

    def __complete_login(self, paket, src):
        def query_function(terminal_id):
            res = self._db_interface.query_terminal(terminal_id)
            terminal_key_b = res[1].encode(UTF8STR)
            return terminal_id, terminal_key_b

        def message_function(user_id, success):
            msg = "Login Terminal: '" + user_id
            if success:
                msg += "' erfolgreich"
            else:
                msg += "' nicht erfolgreich"
            print(msg)

        self.complete_login(paket, src, query_function, message_function)

    def __init_payment(self, session, cipher_paket):
        paket = session.aes_d.decrypt(cipher_paket)
        s = SliceIterator(paket)
        card_number = s.get_slice(16)
        card_key = s.get_slice(64)
        amount = s.get_int()
        reference = s.next_slice().decode(UTF8STR)
        transfer_code = create_alpha_numeric(8)
        session.current_order = PaymentOrder(card_number, card_key, amount, reference, transfer_code)
        answer_paket = encrypt_uneven_block(
            int_to_bytes(PAYMENT_ORDER_ACK) + transfer_code.encode(UTF8STR), session.aes_e)
        self._write_lock.acquire()
        self._udp_socket.sendto(answer_paket, session.ip_and_port)
        self._write_lock.release()

    def __execute_payment(self, session, cipher_paket):
        order = session.current_order
        transfer_code = session.aes_d.decrypt(cipher_paket)[0:8].decode(UTF8STR)

        if order.transfer_code != transfer_code:
            return

        terminal = self._db_interface.query_terminal(session.customer_id)
        account_to = terminal[2]

        res = self._db_interface.query_account_to_card(order.card_number.decode(UTF8STR))

        if res is None:
            return
        else:
            account_from = res[0]
            card_key_from_db = res[1]

        if card_key_from_db != order.card_key:
            print("Kartenzahlung nicht erfolgreich")
            return

        transfer_id = self._transfer_function(DEBIT_CARD_PAYMENT, account_from, account_to, order.amount, order.reference,
                                              query_autoincrement_id=True)
        transfer_code = create_alpha_numeric(8)
        self._db_interface.create_card_payment(transfer_id, order.card_number, transfer_code)

    def __proof_payment(self, session, paket):
        pass

    def card_terminal_routine(self):
        while True:
            try:
                self._read_lock.acquire()
                paket, src = self._udp_socket.recvfrom(1024)
                self._read_lock.release()
                command = int_from_bytes(paket[0:4])
                if command == START_LOGIN:
                    self.__start_login(paket[4:], src)
                elif command == COMPLETE_LOGIN:
                    self.__complete_login(paket[4:], src)
                elif command == CARD_PAYMENT_COMMAND:
                    payment_cmd = int_from_bytes(paket[4:8])
                    session: CardTerminalSession = self._session_list.get_session_from_id(paket[8:16], src)
                    if payment_cmd == INIT_CARD_PAYMENT_COMMAND:
                        self.__init_payment(session, paket[16:])
                    elif payment_cmd == EXECUTE_CARD_PAYMENT_COMMAND:
                        self.__execute_payment(session, paket[16:])
                    elif payment_cmd == PROOF_CARD_PAYMENT_COMMAND:
                        self.__proof_payment(session, paket[16:])
            except:
                traceback.print_exc()
