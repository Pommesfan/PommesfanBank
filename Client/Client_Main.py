import socket
from Client.BankClient import BankClient
from Utils import *

TRANSFER_TYPES = ["Überweisung", "Kartenzahlung"]
COMMANDS = ["Ausloggen", "Abfragen", "Überweisen", "Umsatzübersicht"]


class CustomerClient(BankClient):
    def __init__(self, server_ip, udp_socket, dst):
        super().__init__(udp_socket, dst)
        self.server_ip = server_ip

    def receive_routine(self):
        while True:
            paket, src = self.udp_socket.recvfrom(1024)
            if src != self.dst:
                return
            paket = self.session.aes_d.decrypt(paket)
            cmd = int_from_bytes(paket[0:4])

            if cmd == SHOW_BALANCE_RESPONSE:
                amount_b = paket[4:8]
                print("Kontostand: " + self.format_amount(int_from_bytes(amount_b)))
            elif cmd == TRANSFER_ACK:
                print("Überweisung erfolgreich")
            elif cmd == SEE_TURNOVER_RESPONSE:
                turnover_list_b = self.receive_turnover(paket[4:])
                self.print_turnover(turnover_list_b)
            self.print_commands(COMMANDS)

    def format_amount(self, amount):
        amount = str(amount)
        comma_position = len(amount) - self.session.decimal_position
        return amount[:comma_position] + '.' + amount[comma_position:] + " " + self.session.currency

    def print_turnover(self, turnover_list_b):
        s = SliceIterator(turnover_list_b)
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

    def routine(self, username, password):
        username_b = username.encode(UTF8STR)
        password_b = password.encode(UTF8STR)
        if not self.login(username_b, password_b, dst):
            print("login nicht erfolgreich")
            exit(1)
        self.thread.start()
        self.print_commands(COMMANDS)
        while True:
            banking_command_b = int_to_bytes(BANKING_COMMAND)
            cmd = int(input())
            if cmd == 1:
                paket = int_to_bytes(EXIT_COMMAND)
                self.send_to_server(banking_command_b, paket)
                break
            elif cmd == 2:
                paket = int_to_bytes(SHOW_BALANCE_COMMAND)
                self.send_to_server(banking_command_b, paket)
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
# UDPClientSocket.bind((localIP, localPort))  # for docker
CustomerClient(serverIP, UDPClientSocket, dst).routine(username, password)
