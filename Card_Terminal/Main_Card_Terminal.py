import socket
from Server.BankService import BankClient
from Utils import *

COMMANDS = ["Zahlung vorbereiten", "Zahlung ausführen", "Zahlung nachprüfen", "Logout"]


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

    def print_commands(self):
        print("\nKommando eingeben:\n1: " + COMMANDS[0] + "; 2: " + COMMANDS[1] + "; 3: " + COMMANDS[2] +
              "; 4: " + COMMANDS[3])

    def send_to_server(self, banking_command_b, paket):
        cipher_paket = encrypt_uneven_block(paket, self.aes_e)
        self.udp_socket.sendto(
            banking_command_b + self.session_id + cipher_paket, self.dst)

    def receive_routine(self):
        while True:
            paket, src = self.udp_socket.recvfrom(1024)
            if src != self.dst:
                return
            paket = self.aes_d.decrypt(paket)
            cmd = int_from_bytes(paket[0:4])
            if cmd == PAYMENT_ORDER_ACK:
                print("Transaktion vorbereitet: transfer_code: " + paket[4:12].decode(UTF8STR))
            elif cmd == PAYMENT_EXECUTE_ACK:
                print("erfolgreich ausgeführt")
            elif cmd == PAYMENT_EXECUTE_NACK_TRANSFER_CODE:
                print("transfer code ungültig")
            elif cmd == PAYMENT_EXECUTE_NACK_CARDNUMBER:
                print("Karte nicht registriert")
            elif cmd == PAYMENT_EXECUTE_NACK_CARDKEY:
                print("cardkey passt nicht")
            elif cmd == PAYMENT_PROOF_ACK:
                print("Transaktion verbucht")
            elif cmd == PAYMENT_PROOF_NACK:
                print("Transaktion nicht verbucht")
            self.print_commands()

    def init_payment(self):
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

        paket = (int_to_bytes(INIT_CARD_PAYMENT_COMMAND) + card_id_b + card_key + amount_b + len_refenrence_b + reference_b)
        self.send_to_server(int_to_bytes(CARD_PAYMENT_COMMAND), paket)

    def execute_payment(self):
        print("transfer code eingeben:")
        transfer_code = input()
        paket = int_to_bytes(EXECUTE_CARD_PAYMENT_COMMAND) + transfer_code.encode(UTF8STR)
        self.send_to_server(int_to_bytes(CARD_PAYMENT_COMMAND), paket)

    def proof_payment(self):
        print("transfer code eingeben:")
        transfer_code = input()
        if len(transfer_code) != 8:
            print("transfer code muss 8-stellig sein")
        paket = int_to_bytes(PROOF_CARD_PAYMENT_COMMAND) + transfer_code.encode(UTF8STR)
        self.send_to_server(int_to_bytes(CARD_PAYMENT_COMMAND), paket)

    def logout(self):
        self.send_to_server(int_to_bytes(CARD_PAYMENT_COMMAND), int_to_bytes(EXIT_COMMAND))
        exit(0)

    def routine(self):
        self.thread.start()
        self.print_commands()
        while True:
            cmd = int(input())
            if cmd == 1:
                self.init_payment()
            elif cmd == 2:
                self.execute_payment()
            elif cmd == 3:
                self.proof_payment()
            elif cmd == 4:
                self.logout()


terminal_id_b = '4894d56d4ztr8dt6z7'.encode(UTF8STR)
terminal_key_b = b'redfg465sdg564er89'
serverIP = "127.0.0.1"
serverPort = 20002
dst = (serverIP, serverPort)
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

CardTerminalClient(UDPClientSocket, dst, terminal_id_b, terminal_key_b).routine()
