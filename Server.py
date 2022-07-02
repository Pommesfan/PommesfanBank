import socket
from Utils import *

localIP = "127.0.0.1"
localPort = 20001

max_amount = 2000
customers = [
    ("45321695", "AAAA", "hallo", 6598),
    ("15369754", "BBBB", "hi", 9832),
    ("12498625", "CCCC", "ups", 4682),
    ("49871283", "DDDD", "jesses", 361)
]


def get_customer_index(username, password):
    for i in range(len(customers)):
        c = customers[i]
        if c[1] == username:
            if c[2] == password:
                return i
            else:
                return -1
    return -1


UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))

while True:
    paket, src = UDPServerSocket.recvfrom(1024)
    length_username = int_from_bytes(paket[0:4])
    end_of_username = 4 + length_username
    username = paket[4:end_of_username].decode(UTF8STR)
    start_of_password = end_of_username + 4
    length_of_password = int_from_bytes(paket[end_of_username:start_of_password])
    end_of_password = start_of_password + length_of_password
    password = paket[start_of_password:end_of_password].decode(UTF8STR)

    customer_index = get_customer_index(username, password)
    if customer_index < 0:
        balance = 0
        print("Fehllogin: Nutzer: " + username)
    else:
        print("Kunde: " + username + " hat Kontostand abgefragt")
        balance = customers[customer_index][3]
    UDPServerSocket.sendto(int_to_bytes(balance), src)
