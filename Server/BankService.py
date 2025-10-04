from threading import Thread
from Utils import *


class BankService:
    def __init__(self, db_interface, transfer_function, udp_socket, sessionList, ongoing_session_list,
                 CURRENCY_B, DECIMAL_PLACE_B, read_lock, write_lock, routine):
        self._db_interface = db_interface
        self._transfer_function = transfer_function
        self._udp_socket = udp_socket
        self._session_list = sessionList
        self._ongoing_session_list = ongoing_session_list
        self._CURRENCY_B = CURRENCY_B
        self._DECIMAL_PLACE_B = DECIMAL_PLACE_B
        self._read_lock = read_lock
        self._write_lock = write_lock
        self._thread = Thread(target=routine)

    def start(self):
        self._thread.start()

    def error(self, s):
        self._db_interface.acquire_lock()
        self._db_interface.close()
        self._db_interface.release_lock()
        print(s)
        exit(1)

    def answer_to_client(self, session, paket):
        cipher_paket = encrypt_uneven_block(paket, session.aes_e)
        self._write_lock.acquire()
        self._udp_socket.sendto(cipher_paket, session.ip_and_port)
        self._write_lock.release()

    def start_login(self, s, src, query_function, SessionClass):
        username = s.next_slice().decode(UTF8STR)
        res = query_function(username)
        if res is None:
            return
        customer_id, password_b = res
        session_id = numpy_random.bytes(8)
        session_key = numpy_random.bytes(32)
        aes_e, aes_d = get_aes(session_key)
        aes_from_password_e, aes_from_password_d = get_aes(hashcode(password_b))
        self._ongoing_session_list.add(SessionClass(session_id, session_key, customer_id, src, aes_e, aes_d))

        bank_information_b = int_to_bytes(len(self._CURRENCY_B)) + self._CURRENCY_B + self._DECIMAL_PLACE_B
        paket = session_id + aes_from_password_e.encrypt(session_key) + bank_information_b
        self._write_lock.acquire()
        self._udp_socket.sendto(paket, src)
        self._write_lock.release()

    def complete_login(self, s, src, query_function, message_function):
        session_id = s.get_slice(8)
        received_password_hash = s.get_slice(32)
        session = self._ongoing_session_list.get_session_from_id(session_id, src)
        received_password_hash = session.aes_d.decrypt(received_password_hash)
        self._ongoing_session_list.remove_session(session_id)
        query_res, name, password_b_client = query_function(session.user_id)
        if received_password_hash == hashcode(password_b_client):
            self._session_list.add(session)
            message_function(session.user_id, query_res, True)
            self._write_lock.acquire()
            self._udp_socket.sendto(int_to_bytes(LOGIN_ACK), src)
            self._write_lock.release()
        else:
            message_function(session.user_id,query_res, False)
