import traceback
from Utils import *
from BankService import BankService


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

        self.start_login(paket, src, query_function)

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

    def __transfer_from_debit_card(self, cipher_paket, session):
        paket = session.aes_d.decrypt(cipher_paket)
        terminal = self._db_interface.query_terminal(session.customer_id)
        account_to = terminal[2]

        s = SliceIterator(paket)
        card_number = s.get_slice(16)
        card_key_from_paket = s.get_slice(64)
        amount = s.get_int()
        reference = s.next_slice().decode(UTF8STR)
        res = self._db_interface.query_account_to_card(card_number.decode(UTF8STR))

        if res is None:
            return
        else:
            account_from = res[0]
            card_key_from_db = res[1]

        if card_key_from_db != card_key_from_paket:
            print("Kartenzahlung nicht erfolgreich")
            return

        transfer_id = self._transfer_function(DEBIT_CARD_PAYMENT, account_from, account_to, amount, reference,
                                              query_autoincrement_id=True)
        transfer_code = create_alpha_numeric(8)
        self._db_interface.create_card_payment(transfer_id, card_number, transfer_code)

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
                    session = self._session_list.get_session_from_id(paket[4:12], src)
                    self.__transfer_from_debit_card(paket[12:], session)
            except:
                traceback.print_exc()
