from Server.Sessions import Session
from Utils import *


class BankService:
    def __init__(self, thread, db_interface, transfer_function, udp_socket, sessionList, ongoing_session_list,
                 CURRENCY_B, DECIMAL_PLACE_B, read_lock, write_lock):
        self._thread = thread
        self._db_interface = db_interface
        self._transfer_function = transfer_function
        self._udp_socket = udp_socket
        self._session_list = sessionList
        self._ongoing_session_list = ongoing_session_list
        self._CURRENCY_B = CURRENCY_B
        self._DECIMAL_PLACE_B = DECIMAL_PLACE_B
        self._read_lock = read_lock
        self._write_lock = write_lock

    def start_login(self, paket, src, query_function):
        s = Slice_Iterator(paket)
        username = s.next_slice().decode(UTF8STR)
        res = query_function(username)
        if res is None:
            print("customer id or email '" + username + "' not registered")
            return
        customer_id = res[0]
        session_id = random.bytes(8)
        session_key = random.bytes(32)
        aes_e, aes_d = get_aes(session_key)
        aes_from_password_e, aes_from_password_d = get_aes(hashcode(res[3]))
        self._ongoing_session_list.add(Session(session_id, session_key, customer_id, src, aes_e, aes_d))

        bank_information_b = int_to_bytes(len(self._CURRENCY_B)) + self._CURRENCY_B + self._DECIMAL_PLACE_B
        len_bank_information_b = int_to_bytes(len(bank_information_b))
        paket = len_bank_information_b + bank_information_b + session_id + aes_from_password_e.encrypt(session_key)
        self._write_lock.acquire()
        self._udp_socket.sendto(paket, src)
        self._write_lock.release()

    def complete_login(self, paket, src, query_function):
        s = Slice_Iterator(paket)
        session_id = s.get_slice(8)
        password_cipher = s.next_slice()
        session = self._ongoing_session_list.get_session_from_id(session_id, src)
        password_with_len = session.aes_d.decrypt(password_cipher)
        len_password = int_from_bytes(password_with_len[0:4])
        password_b = password_with_len[4:4 + len_password]
        self._ongoing_session_list.remove_session(session_id)
        res = query_function(session.customer_id)
        customer_password = res[3].encode(UTF8STR)
        customer_name = res[1]
        if password_b == customer_password:
            self._session_list.add(session)
            print("Nutzer: " + session.customer_id + " - " + customer_name + " eingeloggt")
            self._write_lock.acquire()
            self._udp_socket.sendto(int_to_bytes(LOGIN_ACK), src)
            self._write_lock.release()
        else:
            print("Login: " + session.customer_id + " - " + customer_name + " nicht erfolgreich")