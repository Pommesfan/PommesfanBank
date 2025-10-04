import re
import socket
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

        session_id = s.get_slice(8)
        session_key = aes_from_password_d.decrypt(s.get_slice(32))
        aes_e, aes_d = get_aes(session_key)

        # complete login
        password_hash = aes_e.encrypt(password_hash)
        paket = int_to_bytes(COMPLETE_LOGIN) + session_id + password_hash
        self.udp_socket.sendto(paket, dst)

        ack = int_from_bytes(self.udp_socket.recv(4))
        if ack != LOGIN_ACK:
            return False

        currency = s.next_slice().decode(UTF8STR)
        decimal_position = s.get_int()
        self.session = _ClientSession(session_id, aes_e, aes_d, currency, decimal_position)
        return True

    def check_input_amount(self, amount):
        regex = "[0-9]{1,}(\.|\,)[0-9]{" + str(self.session.decimal_position) + "}"
        if re.fullmatch(regex, amount):
            comma_position = len(amount) - self.session.decimal_position
            amount = amount[:comma_position - 1] + amount[comma_position:]
            return int(amount)
        else:
            return -1

    def tcp_on_demand(self, port):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((self.dst[0], port))
        return client

    def receive_turnover(self, port):
        data = b''
        client = self.tcp_on_demand(port)
        length = int_from_bytes(client.recv(4))
        while not length == 0:
            data += self.session.aes_d.decrypt(client.recv(length))
            length = int_from_bytes(client.recv(4))
        client.close()
        return data


class _ClientSession:
    def __init__(self, session_id, aes_e, aes_d, currency, decimal_position):
        self.session_id = session_id
        self.aes_e = aes_e
        self.aes_d = aes_d
        self.currency = currency
        self.decimal_position = decimal_position
