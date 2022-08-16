import socket
from Utils import *

serverIP = "127.0.0.1"
serverPort = 20001

print("Nutzername eingeben:")
username = input()
print("Passwort eingeben:")
password = input()

username_b = username.encode(UTF8STR)
password_b = password.encode(UTF8STR)

dst = (serverIP, serverPort)
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# send login paket
password_hash = hashcode(password)
password_cipher = encrypt(password_b, password_hash)
paket = int_to_bytes(LOGIN_COMMAND) + int_to_bytes(len(username_b)) + username.encode(UTF8STR) \
        + int_to_bytes(len(password_b)) + password_cipher
UDPClientSocket.sendto(paket, dst)

# receive session_id and session_cipher
paket = UDPClientSocket.recv(48)
session_id = paket[0:16]
session_key = decrypt(paket[16:48], password_hash)


def receive_turnover():
    PAKET_LEN = 1472
    initial_paket = decrypt(UDPClientSocket.recv(16), session_key)
    number_of_full_pakets = int_from_bytes(initial_paket[0:4])
    size_of_last_paket = int_from_bytes(initial_paket[4:8])
    b = b''
    for i in range(number_of_full_pakets):
        paket = UDPClientSocket.recv(PAKET_LEN)
        b += (decrypt(paket, session_key))
    if size_of_last_paket != 0:
        paket = UDPClientSocket.recv(size_of_last_paket + number_fill_aes_block_to_16x(size_of_last_paket))
        b += (decrypt(paket, session_key))
    return b


def print_turnover(turnover_list_b):
    s = Slice_Iterator(turnover_list_b)
    while not s.end_reached():
        transmitter_name_len = int_from_bytes(s.get_slice(4))
        transmitter_name = s.get_slice(transmitter_name_len).decode(UTF8STR)
        account_id = s.get_slice(8).decode(UTF8STR)
        amount = int_from_bytes(s.get_slice(4))
        time_stamp = s.get_slice(19).decode(UTF8STR)
        reference_len = int_from_bytes(s.get_slice(4))
        reference = s.get_slice(reference_len).decode(UTF8STR)
        print("Name: " + transmitter_name + "; Kontonummer: " + account_id + "; Wert: " + str(amount) + "; Zeitpunkt: "
              + time_stamp + "; Verwendungszweck: " + reference)
    print()


while True:
    banking_command_b = int_to_bytes(BANKING_COMMAND)
    print("Komandos: 1:Ausloggen, 2:abfragen, 3:überweisen, 4:Umsatzübersicht")
    cmd = int(input())
    if cmd == 1:
        cipher_paket = encrypt(int_to_bytes(EXIT_COMMAND), session_key)
        UDPClientSocket.sendto(banking_command_b + session_id + cipher_paket, dst)
        break
    elif cmd == 2:
        paket_to_encrypt = int_to_bytes(SHOW_BALANCE_COMMAND)
        cipher_paket = encrypt(paket_to_encrypt, session_key)
        paket = banking_command_b + session_id + cipher_paket
        UDPClientSocket.sendto(paket, dst)
        paket = UDPClientSocket.recv(16)
        amount_b = decrypt(paket, session_key)[0:4]
        print("Kontostand: " + str(int_from_bytes(amount_b)))
    elif cmd == 3:
        print("Kontonummer Empfänger:")
        target_account_id_b = input().encode(UTF8STR)
        target_account_id_length_b = int_to_bytes(len(target_account_id_b))
        print("Betrag:")
        amount_b = int_to_bytes(int(input()))
        print("Verwendungszweck:")
        reference = input()
        reference_b = reference.encode(UTF8STR)
        paket = int_to_bytes(TRANSFER_COMMAND) + target_account_id_length_b + target_account_id_b + amount_b + \
            int_to_bytes(len(reference_b)) + reference_b
        cipher_paket = encrypt(paket, session_key)
        UDPClientSocket.sendto(
            banking_command_b + session_id + cipher_paket, dst)
    elif cmd == 4:
        cipher_paket = encrypt(int_to_bytes(SEE_TURNOVER), session_key)
        UDPClientSocket.sendto(
            banking_command_b + session_id + cipher_paket, dst)
        turnover_list_b = receive_turnover()
        print_turnover(turnover_list_b)
