import socket
import sqlite3
from numpy import random
from Utils import *

localIP = "127.0.0.1"
localPort = 20001

max_amount = 2000
con = sqlite3.connect("Hallo.db")
sessions = []


def error(s):
    con.close()
    print(s)
    exit(1)


def init_database():
    con.execute("create table customer(customer_id, customer_name, password, balance)")
    con.commit()

    customers = [
        ("45321695", "AAAA", "hallo", 6598),
        ("15369754", "BBBB", "hi", 9832),
        ("12498625", "CCCC", "ups", 4682),
        ("49871283", "DDDD", "jesses", 361)
    ]
    for c in customers:
        con.execute("insert into customer values ('" + c[0] + "', '" + c[1] + "', '" + c[2] + "', " + str(c[3]) + ")")
    con.commit()


# init_database()


def get_customer_id(username, password):
    response = con.execute("select * from customer where customer_name = '" + username + "'")
    answer = None
    for r in response:
        answer = r
        break

    if answer is None or answer[2] != password:
        return None
    else:
        return answer[0]


def query_balance(customer_id):
    response = con.execute("select balance from customer where customer_id = '" + customer_id + "'")
    answer = None
    for r in response:
        answer = r
        break
    if answer is None:
        error("Abfrage mit nicht existierender Kunden-ID")
    else:
        return answer[0]


def login(paket, src):
    length_username = int_from_bytes(paket[0:4])
    end_of_username = 4 + length_username
    username = paket[4:end_of_username].decode(UTF8STR)
    start_of_password = end_of_username + 4
    length_of_password = int_from_bytes(paket[end_of_username:start_of_password])
    end_of_password = start_of_password + length_of_password
    password = paket[start_of_password:end_of_password].decode(UTF8STR)

    customer_id = get_customer_id(username, password)
    if customer_id is None:
        print("Fehllogin: Nutzer: " + username)
    else:
        print(username + " eingeloggt")
        session = random.bytes(16)
        sessions.append((session, customer_id, src))
        UDPServerSocket.sendto(session, src)


def get_customer_id_from_session(session_id, src):
    for s in sessions:
        if s[0] == session_id and src == s[2]:
            return s[1]
    return None


UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))

while True:
    paket, src = UDPServerSocket.recvfrom(1024)
    command = int_from_bytes(paket[0:4])

    if command == LOGIN_COMMAND:
        login(paket[4:], src)
    elif command == SHOW_BALANCE_COMMAND:
        customer_id = get_customer_id_from_session(paket[4:20], src)
        if customer_id is not None:
            balance = query_balance(customer_id)
            UDPServerSocket.sendto(int_to_bytes(balance), src)
        else:
            error("No customer id to session")
