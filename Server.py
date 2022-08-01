import socket
import traceback
from DB_Interface import DB_Interface
from Utils import *

localIP = "127.0.0.1"
localPort = 20001


class Session:
    def __init__(self, session_id, session_key, customer_id, ip_and_port):
        self.session_id = session_id
        self.session_key = session_key
        self.customer_id = customer_id
        self.ip_and_port = ip_and_port


sessions = []
db_interface = DB_Interface("Hallo.db")
# db_interface.init_database()


def error(s):
    db_interface.close()
    print(s)
    exit(1)


def get_customer_id(username, input_password_cipher, length_of_password):
    answer = db_interface.query_first_item("select * from customer where customer_name = '" + username + "'")

    if answer is None:
        return None

    user_password = answer[2]
    user_password_b = user_password.encode(UTF8STR)
    key = hashcode(user_password)
    input_password_b = decrypt(input_password_cipher, key)

    if user_password_b == input_password_b[:length_of_password]:
        return answer[0], key
    else:
        return None


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
    password_cipher = paket[start_of_password:end_of_password + number_fill_aes_block_to_16x(length_of_password)]

    res = get_customer_id(username, password_cipher, length_of_password)
    if res is None:
        print("Fehllogin: Nutzer: " + username)
    else:
        customer_id = res[0]
        key = res[1]
        print(username + " eingeloggt")
        session_id = random.bytes(16)
        session_key = random.bytes(32)
        session_key_cipher = encrypt(session_key, key)
        sessions.append(Session(session_id, session_key, customer_id, src))
        UDPServerSocket.sendto(session_id + session_key_cipher, src)


def get_session(session_id, src):
    for s in sessions:
        if s.session_id == session_id and s.ip_and_port == src:
            return s
    return None


UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))


def transfer(target_customer_id, customer_id, amount, reference):
    if not db_interface.query_first_item("select * from customer where customer_id = '" + target_customer_id + "'"):
        return

    balance_transmitter = query_balance(customer_id)
    balance_receiver = query_balance(target_customer_id)
    if amount > balance_receiver:
        return
    new_balance_receiver = balance_receiver + amount
    new_balance_transmitter = balance_transmitter - amount
    db_interface.transfer(customer_id, target_customer_id, new_balance_receiver, new_balance_transmitter, amount,
                          reference)


while True:
    paket, src = UDPServerSocket.recvfrom(1024)
    try:
        command = int_from_bytes(paket[0:4])
        if command == LOGIN_COMMAND:
            login(paket[4:], src)
        elif command == BANKING_COMMAND:
            session = get_session(paket[4:20], src)
            customer_id = session.customer_id
            session_key = session.session_key
            paket = decrypt(paket[20:], session_key)
            banking_command = int_from_bytes(paket[0:4])
            if banking_command == SHOW_BALANCE_COMMAND:
                if customer_id is not None:
                    balance = query_balance(customer_id)
                    paket = encrypt(int_to_bytes(balance), session_key)
                    UDPServerSocket.sendto(paket, src)
                else:
                    error("No customer id to session")
            elif banking_command == TRANSFER_COMMAND:
                target_customer_id = paket[4:12].decode(UTF8STR)
                amount = int_from_bytes(paket[12:16])
                reference_length = int_from_bytes(paket[16:20])
                reference = paket[20:20 + reference_length].decode(UTF8STR)
                transfer(target_customer_id, customer_id, amount, reference)
    except:
        traceback.print_exc()
