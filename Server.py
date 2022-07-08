import socket
from numpy import random

from DB_Interface import DB_Interface
from Utils import *

localIP = "127.0.0.1"
localPort = 20001


class Session:
    def __init__(self, session_id, customer_id, ip_and_port):
        self.session_id = session_id
        self.customer_id = customer_id
        self.ip_and_port = ip_and_port


sessions = []
db_interface = DB_Interface("Hallo.db")
# db_interface.init_database()


def error(s):
    db_interface.close()
    print(s)
    exit(1)


def get_customer_id(username, password):
    answer = db_interface.query_first_item("select * from customer where customer_name = '" + username + "'")

    if answer is None or answer[2] != password:
        return None
    else:
        return answer[0]


def query_balance(customer_id):
    answer = db_interface.query_first_item("select balance from customer where customer_id = '" + customer_id + "'")
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
        session_id = random.bytes(16)
        sessions.append(Session(session_id, customer_id, src))
        UDPServerSocket.sendto(session_id, src)


def get_customer_id_from_session(session_id, src):
    for s in sessions:
        if s.session_id == session_id and s.ip_and_port == src:
            return s.customer_id
    return None


UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))


def transfer(target_customer_id, customer_id, amount):
    if not db_interface.query_first_item("select * from customer where customer_id = '" + target_customer_id + "'"):
        return

    balance_transmitter = query_balance(customer_id)
    balance_receiver = query_balance(target_customer_id)
    if amount > balance_receiver:
        return
    new_balance_receiver = balance_receiver + amount
    new_balance_transmitter = balance_transmitter - amount
    db_interface.transfer(customer_id, target_customer_id, new_balance_receiver, new_balance_transmitter)


while True:
    paket, src = UDPServerSocket.recvfrom(1024)
    command = int_from_bytes(paket[0:4])

    if command == LOGIN_COMMAND:
        login(paket[4:], src)
    else:
        customer_id = get_customer_id_from_session(paket[4:20], src)
        if command == SHOW_BALANCE_COMMAND:
            if customer_id is not None:
                balance = query_balance(customer_id)
                UDPServerSocket.sendto(int_to_bytes(balance), src)
            else:
                error("No customer id to session")
        elif command == TRANSFER_COMMAND:
            target_customer_id = paket[20:28].decode(UTF8STR)
            amount = int_from_bytes(paket[28:32])
            transfer(target_customer_id, customer_id, amount)
