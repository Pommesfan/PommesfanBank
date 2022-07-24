import socket
from Crypto.Cipher import AES
from Utils import *

serverIP = "127.0.0.1"
serverPort = 20001

print("Nutzername eingeben:")
username = input()
print("Passwort eingeben:")
password = input()

dst = (serverIP, serverPort)
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)


def encrypt_password(password):
    password_hash = hashcode(password)
    password_b = password.encode(UTF8STR)
    password_length = len(password)

    obj1 = AES.new(password_hash, AES.MODE_CBC, 'This is an IV456')

    return obj1.encrypt(password_b + random.bytes(number_fill_aes_block_to_16x(password_length)))


password_cipher = encrypt_password(password)

paket = int_to_bytes(LOGIN_COMMAND) + int_to_bytes(len(username)) + username.encode(UTF8STR) \
        + int_to_bytes(len(password)) + password_cipher
UDPClientSocket.sendto(paket, dst)
session = UDPClientSocket.recv(16)

while True:
    banking_command_b = int_to_bytes(BANKING_COMMAND)
    print("Komandos: 1:abfragen, 2:überweisen")
    cmd = int(input())
    if cmd == 1:
        UDPClientSocket.sendto(banking_command_b + int_to_bytes(SHOW_BALANCE_COMMAND) + session, dst)
        amount_b = UDPClientSocket.recv(4)
        print("Kontostand: " + str(int_from_bytes(amount_b)))
    elif cmd == 2:
        print("Kundennummer Empfänger:")
        target_customer_id = input().encode(UTF8STR)
        print("Betrag:")
        amount = int_to_bytes(int(input()))
        UDPClientSocket.sendto(
            banking_command_b + int_to_bytes(TRANSFER_COMMAND) + session + target_customer_id + amount, dst)
