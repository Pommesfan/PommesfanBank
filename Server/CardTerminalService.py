import traceback
from threading import Thread
import Utils
from Utils import Slice_Iterator, UTF8STR, hashcode, DEBIT_CARD_PAYMENT
from BankService import BankService


class CardTerminalService(BankService):
    def __init__(self, db_interface, transfer_function, udp_socket, read_lock, session_list, ongoing_session_list,
                 CURRENCY_B, DECIMAL_PLACE_B):
        thread = Thread(target=self.card_terminal_routine)
        super().__init__(thread, db_interface, transfer_function, udp_socket, session_list, ongoing_session_list,
                         CURRENCY_B, DECIMAL_PLACE_B, read_lock, None)

    def start(self):
        self._thread.start()

    def __transfer_from_debit_card(self, paket):
        s = Slice_Iterator(paket)
        terminal_id = s.next_slice().decode(UTF8STR)
        terminal = self._db_interface.query_terminal(terminal_id)

        if terminal is None:
            return

        terminal_key = terminal[1]
        account_to = terminal[2]

        aes_e, aes_d = Utils.get_aes(hashcode(terminal_key))

        cipher_paket = s.next_slice()
        paket = aes_d.decrypt(cipher_paket)
        s = Slice_Iterator(paket)
        card_number = s.get_slice(16)
        card_key_from_paket = s.get_slice(64)
        res = self._db_interface.query_account_to_card(card_number.decode(UTF8STR))
        if res is None:
            return
        else:
            account_from = res[0]
            card_key_from_db = res[1]

        if card_key_from_db != card_key_from_paket:
            return
        amount = s.get_int()
        reference = s.next_slice().decode(UTF8STR)

        self._transfer_function(DEBIT_CARD_PAYMENT, account_from, account_to, amount, reference)

    def card_terminal_routine(self):
        while True:
            try:
                self._read_lock.acquire()
                paket, src = self._udp_socket.recvfrom(1024)
                self._read_lock.release()
                self.__transfer_from_debit_card(paket)
            except:
                traceback.print_exc()
