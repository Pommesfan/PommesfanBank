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

paket = int_to_bytes(LOGIN_COMMAND) + int_to_bytes(len(username)) + username.encode(UTF8STR)\
        + int_to_bytes(len(password)) + password.encode(UTF8STR)
UDPClientSocket.sendto(paket, dst)
session = UDPClientSocket.recv(16)

while True:
    print("Komandos: 1:abfragen, 2:überweisen")
    cmd = int(input())
    if cmd == 1:
        UDPClientSocket.sendto(int_to_bytes(SHOW_BALANCE_COMMAND) + session, dst)
        amount_b = UDPClientSocket.recv(4)
        print("Kontostand: " + str(int_from_bytes(amount_b)))
    elif cmd == 2:
        print("Kundennummer Empfänger:")
        target_customer_id = input().encode(UTF8STR)
        print("Betrag:")
        amount = int_to_bytes(int(input()))
        UDPClientSocket.sendto(int_to_bytes(TRANSFER_COMMAND) + session + target_customer_id + amount, dst)

