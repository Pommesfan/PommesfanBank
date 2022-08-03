import socket
from Utils import *

serverIP = "127.0.0.1"
serverPort = 20001

print("Nutzername eingeben:")
username = input()
print("Passwort eingeben:")
password = input()

dst = (serverIP, serverPort)
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)


def encrypt_password(password, password_hash):
    password_b = password.encode(UTF8STR)
    return encrypt(password_b, password_hash)


# send login paket
password_hash = hashcode(password)
password_cipher = encrypt_password(password, password_hash)
paket = int_to_bytes(LOGIN_COMMAND) + int_to_bytes(len(username)) + username.encode(UTF8STR) \
        + int_to_bytes(len(password)) + password_cipher
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
    counter = 0
    while turnover_list_b[counter:counter + 4] != TERMINATION:
        customer_id = turnover_list_b[counter:counter+8].decode(UTF8STR)
        counter+=8
        amount = int_from_bytes(turnover_list_b[counter:counter+4])
        counter+=4
        time_stamp = turnover_list_b[counter: counter + 19].decode(UTF8STR)
        counter += 19
        reference_len = int_from_bytes(turnover_list_b[counter:counter+4])
        counter += 4
        reference = turnover_list_b[counter:counter + reference_len].decode(UTF8STR)
        counter += reference_len
        print("Kundennummer: " + customer_id + "; Wert: " + str(amount) + "; Zeitpunkt: " + time_stamp +
              "; Verwendungszweck: " + reference)
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
        print("Kundennummer Empfänger:")
        target_customer_id = input().encode(UTF8STR)
        print("Betrag:")
        amount = int_to_bytes(int(input()))
        print("Verwendungszweck:")
        reference = input()
        paket = int_to_bytes(TRANSFER_COMMAND) + target_customer_id + amount + int_to_bytes(len(reference))\
            + reference.encode(UTF8STR)
        cipher_paket = encrypt(paket, session_key)
        UDPClientSocket.sendto(
            banking_command_b + session_id + cipher_paket, dst)
    elif cmd == 4:
        cipher_paket = encrypt(int_to_bytes(SEE_TURNOVER), session_key)
        UDPClientSocket.sendto(
            banking_command_b + session_id + cipher_paket, dst)
        turnover_list_b = receive_turnover()
        print_turnover(turnover_list_b)
