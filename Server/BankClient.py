from threading import Thread

from Utils import *


class BankClient:
    def __init__(self, udp_socket, dst):
        self.udp_socket = udp_socket
        self.dst = dst
        self.thread = Thread(target=self.receive_routine)
        self.session = None

    def print_commands(self, commands):
        s = "\nKommandos: "
        for i in range(len(commands)):
            s += str(i + 1) + ": " + commands[i] + ", "
        print(s)

    def receive_routine(self):
        pass

    def send_to_server(self, banking_command_b, paket):
        cipher_paket = encrypt_uneven_block(paket, self.session.aes_e)
        self.udp_socket.sendto(
            banking_command_b + self.session.session_id + cipher_paket, self.dst)

    def login(self, username_b, password_b, dst):
        # start login paket
        password_hash = hashcode(password_b)
        aes_from_password_e, aes_from_password_d = get_aes(password_hash)
        paket = int_to_bytes(START_LOGIN) + int_to_bytes(len(username_b)) + username_b
        self.udp_socket.sendto(paket, dst)

        # receive start login response
        paket = self.udp_socket.recv(96)
        s = SliceIterator(paket)
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
        self.session = _ClientSession(session_id, aes_e, aes_d)
        return bank_information


class _ClientSession:
    def __init__(self, session_id, aes_e, aes_d):
        self.session_id = session_id
        self.aes_e = aes_e
        self.aes_d = aes_d
