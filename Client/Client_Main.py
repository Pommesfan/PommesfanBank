import socket

from Server.BankService import BankClient
from Utils import *
import re

TRANSFER_TYPES = ["Überweisung", "Kartenzahlung"]
serverIP = "127.0.0.1"
serverPort = 20001

localIP = "127.0.0.2"
localPort = 20002

print("Kundennummer oder E-Mail-Adresse eingeben:")
username = input()
print("Passwort eingeben:")
password = input()

dst = (serverIP, serverPort)
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.bind((localIP, localPort))  # for docker


class Customer_Client(BankClient):
    def __init__(self, udp_socket, dst):
        super().__init__(udp_socket)
        username_b = username.encode(UTF8STR)
        password_b = password.encode(UTF8STR)
        bank_information, session_id, aes_e, aes_d = self.login(username_b, password_b, dst)
        bank_information = bank_information
        self.session_id = session_id
        self.aes_e = aes_e
        self.aes_d = aes_d
        s = Slice_Iterator(bank_information)
        self.currency = s.next_slice().decode(UTF8STR)
        self.decimal_position = s.get_int()

    def format_amount(self, amount):
        amount = str(amount)
        comma_position = len(amount) - self.decimal_position
        return amount[:comma_position] + '.' + amount[comma_position:] + " " + self.currency

    def check_input_amount(self, amount):
        regex = "[0-9]{1,}(\.|\,)[0-9]{" + str(self.decimal_position) + "}"
        if re.fullmatch(regex, amount):
            comma_position = len(amount) - self.decimal_position
            amount = amount[:comma_position - 1] + amount[comma_position:]
            return int(amount)
        else:
            return -1

    def tcp_on_demand(self):
        initial_paket = self.aes_d.decrypt(UDPClientSocket.recv(16))
        tcp_server_port = int_from_bytes(initial_paket[0:4])
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((serverIP, tcp_server_port))
        return client

    def receive_turnover(self):
        data = b''
        client = self.tcp_on_demand()
        length = int_from_bytes(client.recv(4))
        while not length == 0:
            data += self.aes_d.decrypt(client.recv(length))
            length = int_from_bytes(client.recv(4))
        client.close()
        return data

    def print_turnover(self, turnover_list_b):
        s = Slice_Iterator(turnover_list_b)
        while not s.end_reached():
            transfer_type = s.get_int()
            transmitter_name = s.next_slice().decode(UTF8STR)
            account_id = s.get_slice(8).decode(UTF8STR)
            amount = s.get_int()
            time_stamp = s.get_slice(19).decode(UTF8STR)
            reference = s.next_slice().decode(UTF8STR)
            print(TRANSFER_TYPES[transfer_type - 1] + " - Name: " + transmitter_name + "; Kontonummer: " + account_id +
                  "; Wert: " + self.format_amount(
                amount) + "; Zeitpunkt: " + time_stamp + "; Verwendungszweck: " + reference)
        print()

    def send_to_server(self, banking_command_b, paket):
        cipher_paket = encrypt_uneven_block(paket, self.aes_e)
        UDPClientSocket.sendto(
            banking_command_b + self.session_id + cipher_paket, dst)

    def routine(self):
        while True:
            banking_command_b = int_to_bytes(BANKING_COMMAND)
            print("Komandos: 1:Ausloggen, 2:abfragen, 3:überweisen, 4:Umsatzübersicht")
            cmd = int(input())
            if cmd == 1:
                paket = int_to_bytes(EXIT_COMMAND)
                self.send_to_server(banking_command_b, paket)
                break
            elif cmd == 2:
                paket = int_to_bytes(SHOW_BALANCE_COMMAND)
                self.send_to_server(banking_command_b, paket)
                paket = UDPClientSocket.recv(16)
                amount_b = self.aes_d.decrypt(paket)[0:4]
                print("Kontostand: " + self.format_amount(int_from_bytes(amount_b)))
            elif cmd == 3:
                print("Kontonummer/E-Mail-Adresse Empfänger:")
                target_account_id_b = input().encode(UTF8STR)
                target_account_id_length_b = int_to_bytes(len(target_account_id_b))
                print("Betrag:")
                amount = self.check_input_amount(input())
                if amount < 1:
                    print("Ungültige Angabe bei Betrag")
                    continue
                amount_b = int_to_bytes(amount)
                print("Verwendungszweck:")
                reference = input()
                reference_b = reference.encode(UTF8STR)
                paket = int_to_bytes(TRANSFER_COMMAND) + target_account_id_length_b + target_account_id_b + amount_b + \
                        int_to_bytes(len(reference_b)) + reference_b
                self.send_to_server(banking_command_b, paket)
            elif cmd == 4:
                paket = int_to_bytes(SEE_TURNOVER)
                self.send_to_server(banking_command_b, paket)
                turnover_list_b = self.receive_turnover()
                self.print_turnover(turnover_list_b)


Customer_Client(UDPClientSocket, dst).routine()
