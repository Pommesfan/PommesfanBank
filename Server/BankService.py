from threading import Thread

from Server.Sessions import Session
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
        password_b = res[3].encode(UTF8STR)
        aes_from_password_e, aes_from_password_d = get_aes(hashcode(password_b))
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


class BankClient:
    def __init__(self, udp_socket, dst):
        self.udp_socket = udp_socket
        self.dst = dst

    def login(self, username_b, password_b, dst):
        # start login paket
        password_hash = hashcode(password_b)
        aes_from_password_e, aes_from_password_d = get_aes(password_hash)
        paket = int_to_bytes(START_LOGIN) + int_to_bytes(len(username_b)) + username_b
        self.udp_socket.sendto(paket, dst)

        # receive start login response
        paket = self.udp_socket.recv(96)
        s = Slice_Iterator(paket)
        bank_information = s.next_slice()
        session_id = s.get_slice(8)
        session_key = aes_from_password_d.decrypt(s.get_slice(32))
        aes_e, aes_d = get_aes(session_key)

        # complete login
        password_cipher = encrypt_uneven_block(int_to_bytes(len(password_b)) + password_b, aes_e)
        paket = int_to_bytes(COMPLETE_LOGIN) + session_id + int_to_bytes(len(password_cipher)) + password_cipher
        self.udp_socket.sendto(paket, dst)

        ack = int_from_bytes(self.udp_socket.recv(4))
        if ack != LOGIN_ACK:
            exit(1)
        return bank_information, session_id, aes_e, aes_d
