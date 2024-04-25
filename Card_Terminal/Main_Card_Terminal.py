import socket

from Server.BankService import BankClient
from Utils import *


class CardTerminalClient(BankClient):
    def __init__(self, udp_socket, dst, terminal_id_b, terminal_key_b):
        super().__init__(udp_socket, dst)
        self.udp_socket = udp_socket
        self.terminal_id_b = terminal_id_b
        self.terminal_key_b = terminal_key_b
        bank_information, session_id, aes_e, aes_d = self.login(terminal_id_b, terminal_key_b, dst)
        self.bank_information = bank_information
        self.session_id = session_id
        self.aes_e = aes_e
        self.aes_d = aes_d

    def send_to_server(self, banking_command_b, paket):
        cipher_paket = encrypt_uneven_block(paket, self.aes_e)
        self.udp_socket.sendto(
            banking_command_b + self.session_id + cipher_paket, self.dst)

    def routine(self):
        print("Pfad Karte:")
        f = open(input(), "rb")
        card = f.read(80)
        card_id_b = card[:16]
        card_key_cipher = card[16:80]
        print("PIN:")
        pin = input()
        aes_pin_e, aes_pin_d = get_aes(hashcode(pin.encode(UTF8STR)))
        card_key = aes_pin_d.decrypt(card_key_cipher)
        print("Preis:")

        amount_b = int_to_bytes(int(input()))
        print("Verwendungszweck:")
        reference_b = input().encode(UTF8STR)
        len_refenrence_b = int_to_bytes(len(reference_b))

        paket = card_id_b + card_key + amount_b + len_refenrence_b + reference_b
        self.send_to_server(int_to_bytes(CARD_PAYMENT_COMMAND), paket)


terminal_id_b = '4894d56d4ztr8dt6z7'.encode(UTF8STR)
terminal_key_b = b'redfg465sdg564er89'
serverIP = "127.0.0.1"
serverPort = 20002
dst = (serverIP, serverPort)
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

CardTerminalClient(UDPClientSocket, dst, terminal_id_b, terminal_key_b).routine()
