import socket
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

username_b = username.encode(UTF8STR)
password_b = password.encode(UTF8STR)

dst = (serverIP, serverPort)
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPClientSocket.bind((localIP, localPort))  # for docker

# send login paket
password_hash = hashcode(password)
aes_from_password = get_aes(password_hash)
password_cipher = encrypt_uneven_block(password_b, aes_from_password)
paket = int_to_bytes(LOGIN_COMMAND) + int_to_bytes(len(username_b)) + username.encode(UTF8STR) \
        + int_to_bytes(len(password_b)) + password_cipher
UDPClientSocket.sendto(paket, dst)

# receive session_id and session_cipher
paket = UDPClientSocket.recv(96)
s = Slice_Iterator(paket)
session_id = s.get_slice(8)
session_key = aes_from_password.decrypt(s.get_slice(32))
aes = get_aes(session_key)
currency = s.next_slice().decode(UTF8STR)
decimal_position = s.get_int()


def format_amount(amount):
    global decimal_position
    amount = str(amount)
    comma_position = len(amount) - decimal_position
    return amount[:comma_position] + '.' + amount[comma_position:] + " " + currency


def check_input_amount(amount):
    regex = "[0-9]{1,}(\.|\,)[0-9]{" + str(decimal_position) + "}"
    if re.fullmatch(regex, amount):
        comma_position = len(amount) - decimal_position
        amount = amount[:comma_position - 1] + amount[comma_position:]
        return int(amount)
    else:
        return -1


def tcp_on_demand():
    initial_paket = aes.decrypt(UDPClientSocket.recv(16))
    tcp_server_port = int_from_bytes(initial_paket[0:4])
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((serverIP, tcp_server_port))
    return client


def receive_turnover():
    data = b''
    client = tcp_on_demand()
    length = int_from_bytes(client.recv(4))
    while not length == 0:
        data += aes.decrypt(client.recv(length))
        length = int_from_bytes(client.recv(4))
    client.close()
    return data


def print_turnover(turnover_list_b):
    s = Slice_Iterator(turnover_list_b)
    while not s.end_reached():
        transfer_type = s.get_int()
        transmitter_name = s.next_slice().decode(UTF8STR)
        account_id = s.get_slice(8).decode(UTF8STR)
        amount = s.get_int()
        time_stamp = s.get_slice(19).decode(UTF8STR)
        reference = s.next_slice().decode(UTF8STR)
        print(TRANSFER_TYPES[transfer_type - 1] + " - Name: " + transmitter_name + "; Kontonummer: " + account_id +
              "; Wert: " + format_amount(amount) + "; Zeitpunkt: " + time_stamp + "; Verwendungszweck: " + reference)
    print()


def send_to_server(paket):
    cipher_paket = encrypt_uneven_block(paket, aes)
    UDPClientSocket.sendto(
        banking_command_b + session_id + cipher_paket, dst)


if __name__ == '__main__':
    while True:
        banking_command_b = int_to_bytes(BANKING_COMMAND)
        print("Komandos: 1:Ausloggen, 2:abfragen, 3:überweisen, 4:Umsatzübersicht")
        cmd = int(input())
        if cmd == 1:
            paket = int_to_bytes(EXIT_COMMAND)
            send_to_server(paket)
            break
        elif cmd == 2:
            paket = int_to_bytes(SHOW_BALANCE_COMMAND)
            send_to_server(paket)
            paket = UDPClientSocket.recv(16)
            amount_b = aes.decrypt(paket)[0:4]
            print("Kontostand: " + format_amount(int_from_bytes(amount_b)))
        elif cmd == 3:
            print("Kontonummer/E-Mail-Adresse Empfänger:")
            target_account_id_b = input().encode(UTF8STR)
            target_account_id_length_b = int_to_bytes(len(target_account_id_b))
            print("Betrag:")
            amount = check_input_amount(input())
            if amount < 1:
                print("Ungültige Angabe bei Betrag")
                continue
            amount_b = int_to_bytes(amount)
            print("Verwendungszweck:")
            reference = input()
            reference_b = reference.encode(UTF8STR)
            paket = int_to_bytes(TRANSFER_COMMAND) + target_account_id_length_b + target_account_id_b + amount_b + \
                    int_to_bytes(len(reference_b)) + reference_b
            send_to_server(paket)
        elif cmd == 4:
            paket = int_to_bytes(SEE_TURNOVER)
            send_to_server(paket)
            turnover_list_b = receive_turnover()
            print_turnover(turnover_list_b)
