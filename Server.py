import socket
import traceback
from DB_Interface import DB_Interface
from Utils import *
from Sessions import *
from threading import Thread, Lock

NUMBER_OF_THREADS = 4
localIP = "127.0.0.1"
localPort = 20001
socket_read_lock = Lock()
socket_write_lock = Lock()

session_list = SessionList()
db_interface = DB_Interface("Pommesfan_Bank_DB.db")
# db_interface.init_database()

UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))


def error(s):
    db_interface.acquire_lock()
    db_interface.close()
    db_interface.release_lock()
    print(s)
    exit(1)


def get_customer_id(username, input_password_cipher, length_of_password):
    db_interface.acquire_lock()
    answer = db_interface.query_customer_by_name(username)
    db_interface.release_lock()

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



def login(paket, src):
    s = Slice_Iterator(paket)
    length_username = int_from_bytes(s.get_slice(4))
    username = s.get_slice(length_username).decode(UTF8STR)
    length_of_password = int_from_bytes(s.get_slice(4))
    password_cipher = s.get_slice(length_of_password + number_fill_aes_block_to_16x(length_of_password))

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
        session_list.add(Session(session_id, session_key, customer_id, src))

        socket_write_lock.acquire()
        UDPServerSocket.sendto(session_id + session_key_cipher, src)
        socket_write_lock.release()


def transfer(customer_id, slice_iterator):
    target_customer_id = slice_iterator.get_slice(8).decode(UTF8STR)
    amount = int_from_bytes(slice_iterator.get_slice(4))
    reference_length = int_from_bytes(slice_iterator.get_slice(4))
    reference = slice_iterator.get_slice(reference_length).decode(UTF8STR)

    db_interface.acquire_lock()
    if not db_interface.query_customer_by_id(target_customer_id):
        return

    balance_transmitter = db_interface.query_balance(customer_id)[0]
    balance_receiver = db_interface.query_balance(target_customer_id)[0]
    if amount > balance_transmitter:
        return
    new_balance_receiver = balance_receiver + amount
    new_balance_transmitter = balance_transmitter - amount
    db_interface.transfer(customer_id, target_customer_id, new_balance_receiver, new_balance_transmitter, amount,
                          reference)
    db_interface.release_lock()


def resume_turnover(customer_id, src, session_key):
    PAKET_LEN = 1472
    db_interface.acquire_lock()
    res = db_interface.query_turnover(customer_id)
    # make large bytes array of all information
    b = b''
    for x in res:
        reference = x[3]
        customer_id_b = x[0].encode(UTF8STR)
        amount_b = int_to_bytes(x[1])
        timestamp_b = x[2].encode(UTF8STR)
        reference_b = reference.encode(UTF8STR)
        reference_length_b = int_to_bytes(len(reference_b))
        b += (customer_id_b + amount_b + timestamp_b + reference_length_b + reference_b)
    b += TERMINATION
    db_interface.release_lock()

    # split array into pakets and send
    def send_function(single_paket):
        socket_write_lock.acquire()
        UDPServerSocket.sendto(encrypt(single_paket, session_key), src)
        socket_write_lock.release()

    split_pakets(b, send_function, PAKET_LEN)


def user_exit(session):
    db_interface.acquire_lock()
    name = db_interface.query_customer_name(session.customer_id)
    db_interface.release_lock()
    if session_list.remove_session(session.session_id) == -1:
        error("remove session: session_id not found")
    print(name[0] + " ausgeloggt")


def show_balance(session):
    if session.customer_id is not None:
        db_interface.acquire_lock()
        balance = db_interface.query_balance(session.customer_id)[0]
        db_interface.release_lock()
        paket = encrypt(int_to_bytes(balance), session.session_key)

        socket_write_lock.acquire()
        UDPServerSocket.sendto(paket, session.ip_and_port)
        socket_write_lock.release()
    else:
        error("No customer id to session")


def server_routine():
    while True:
        socket_read_lock.acquire()
        paket, src = UDPServerSocket.recvfrom(1024)
        socket_read_lock.release()

        try:
            command = int_from_bytes(paket[0:4])
            if command == LOGIN_COMMAND:
                login(paket[4:], src)
            elif command == BANKING_COMMAND:
                session = session_list.get_session_from_id(paket[4:20], src)
                # session was removed due to logout
                if session is None:
                    continue
                customer_id = session.customer_id
                session_key = session.session_key
                paket = decrypt(paket[20:], session_key)
                banking_command = int_from_bytes(paket[0:4])
                if banking_command == EXIT_COMMAND:
                    user_exit(session)
                elif banking_command == SHOW_BALANCE_COMMAND:
                    show_balance(session)
                elif banking_command == TRANSFER_COMMAND:
                    s = Slice_Iterator(paket, counter=4)
                    transfer(customer_id, s)
                elif banking_command == SEE_TURNOVER:
                    resume_turnover(customer_id, src, session_key)
        except:
            traceback.print_exc()


for i in range(NUMBER_OF_THREADS):
    Thread(target=server_routine).start()
