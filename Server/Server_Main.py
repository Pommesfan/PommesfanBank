import socket
import traceback
from DB_Interface import *
from Utils import *
from Sessions import *
from threading import Thread, Lock

NUMBER_OF_THREADS = 4
localIP = "127.0.0.1"
local_port_customer = 20001
local_port_terminal = 20002
CURRENCY_B = "EURO".encode(UTF8STR)
DECIMAL_PLACE_B = int_to_bytes(2)
customer_socket_read_lock = Lock()
customer_socket_write_lock = Lock()
card_terminal_socket_read_lock = Lock()
card_terminal_socket_write_lock = Lock()

session_list = SessionList()
db_interface = DB_Interface("./Pommesfan_Bank_DB.db")
# db_interface.init_database()

customer_udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
customer_udp_socket.bind((localIP, local_port_customer))
terminal_udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
terminal_udp_socket.bind((localIP, local_port_terminal))


def send_to_customer(paket, session):
    cipher_paket = encrypt(paket, session.session_key)
    customer_socket_write_lock.acquire()
    customer_udp_socket.sendto(cipher_paket, session.ip_and_port)
    customer_socket_write_lock.release()


def error(s):
    db_interface.acquire_lock()
    db_interface.close()
    db_interface.release_lock()
    print(s)
    exit(1)


def get_customer_from_username(username, input_password_cipher, length_of_password):
    db_interface.acquire_lock()
    if '@' in username:
        answer = db_interface.query_customer(username, "email")
    else:
        answer = db_interface.query_customer(username, "customer_id")
    db_interface.release_lock()

    if answer is None:
        return None

    user_password = answer[3]
    user_password_b = user_password.encode(UTF8STR)
    key = hashcode(user_password)
    input_password_b = decrypt(input_password_cipher, key)

    if user_password_b == input_password_b[:length_of_password]:
        return answer[0], key, answer[1]
    else:
        return None


def login(paket, src):
    s = Slice_Iterator(paket)
    length_username = int_from_bytes(s.get_slice(4))
    username = s.get_slice(length_username).decode(UTF8STR)
    length_of_password = int_from_bytes(s.get_slice(4))
    password_cipher = s.get_slice(length_of_password + number_fill_aes_block_to_16x(length_of_password))

    res = get_customer_from_username(username, password_cipher, length_of_password)
    if res is None:
        print("Fehllogin: Nutzer: " + username)
    else:
        customer_id = res[0]
        key = res[1]
        customer_name = res[2]
        print("Nutzer: " + customer_id + " - " + customer_name + " eingeloggt")
        session_id = random.bytes(8)
        session_key = random.bytes(32)
        session_key_cipher = encrypt(session_key, key)
        session_list.add(Session(session_id, session_key, customer_id, src))
        bank_information = int_to_bytes(len(CURRENCY_B)) + CURRENCY_B + DECIMAL_PLACE_B

        customer_socket_write_lock.acquire()
        customer_udp_socket.sendto(session_id + session_key_cipher + bank_information, src)
        customer_socket_write_lock.release()


def transfer(transmitter_account_id, receiver_account_id, amount, reference):
    db_interface.acquire_lock()
    balance_transmitter = db_interface.query_balance(transmitter_account_id)[0]
    balance_receiver = db_interface.query_balance(receiver_account_id)
    if amount < 1 or transmitter_account_id == receiver_account_id or balance_receiver is None \
            or amount > balance_transmitter:
        db_interface.release_lock()
        return

    balance_receiver = balance_receiver[0]
    new_balance_receiver = balance_receiver + amount
    new_balance_transmitter = balance_transmitter - amount
    db_interface.transfer(transmitter_account_id, receiver_account_id, new_balance_receiver, new_balance_transmitter,
                          amount, reference)
    db_interface.release_lock()


def transfer_from_session(session, slice_iterator):
    receiver_account_len = int_from_bytes(slice_iterator.get_slice(4))
    receiver_account_id = slice_iterator.get_slice(receiver_account_len).decode(UTF8STR)
    amount = int_from_bytes(slice_iterator.get_slice(4))
    reference_length = int_from_bytes(slice_iterator.get_slice(4))
    reference = slice_iterator.get_slice(reference_length).decode(UTF8STR)
    transmitter_account_id = db_interface.query_account_to_customer(session.customer_id, "customer_id")[0]

    if '@' in receiver_account_id:
        res = db_interface.query_account_to_customer(receiver_account_id, "email")
        if res is None:
            return
        receiver_account_id = res[0]

    transfer(transmitter_account_id, receiver_account_id, amount, reference)


def transfer_from_debit_card(paket):
    s = Slice_Iterator(paket)
    len_terminal_id = int_from_bytes(s.get_slice(4))
    terminal_id = s.get_slice(len_terminal_id).decode(UTF8STR)
    terminal = db_interface.query_terminal(terminal_id)

    if terminal is None:
        return

    terminal_key = terminal[1]
    account_to = terminal[2]

    len_cipher_paket = int_from_bytes(s.get_slice(4))
    cipher_paket = s.get_slice(len_cipher_paket)
    paket = decrypt(cipher_paket, hashcode(terminal_key))
    s = Slice_Iterator(paket)
    card_number = s.get_slice(16)
    card_key_from_paket = s.get_slice(64)
    res = db_interface.query_account_to_card(card_number.decode(UTF8STR))
    if res is None:
        return
    else:
        account_from = res[0]
        card_key_from_db = res[1]

    if card_key_from_db != card_key_from_paket:
        return
    amount = int_from_bytes(s.get_slice(4))
    len_reference = int_from_bytes(s.get_slice(4))
    reference = s.get_slice(len_reference).decode(UTF8STR)

    transfer(account_from, account_to, amount, reference)


def resume_turnover(customer_id, session):
    PAKET_LEN = 1472
    db_interface.acquire_lock()
    account_id = db_interface.query_account_to_customer(customer_id, "customer_id")[0]
    res = db_interface.query_turnover(account_id)
    # make large bytes array of all information
    b = b''
    for x in res:
        reference = x[4]
        transmitter_name_b = x[0].encode(UTF8STR)
        account_id_b = x[1].encode(UTF8STR)
        amount_b = int_to_bytes(x[2])
        timestamp_b = x[3].encode(UTF8STR)
        transmitter_name_length_b = int_to_bytes(len(transmitter_name_b))
        reference_b = reference.encode(UTF8STR)
        reference_length_b = int_to_bytes(len(reference_b))
        b += (transmitter_name_length_b + transmitter_name_b + account_id_b + amount_b + timestamp_b +
              reference_length_b + reference_b)
    b += TERMINATION
    db_interface.release_lock()

    # split array into pakets and send
    def send_function(single_paket):
        send_to_customer(single_paket, session)

    split_pakets(b, send_function, PAKET_LEN)


def user_exit(session):
    db_interface.acquire_lock()
    name = db_interface.query_customer_name(session.customer_id)
    db_interface.release_lock()
    if session_list.remove_session(session.session_id) == -1:
        error("remove session: session_id not found")
    print("Nutzer: " + session.customer_id + " - " + name[0] + " ausgeloggt")


def show_balance(session):
    if session.customer_id is not None:
        db_interface.acquire_lock()
        account_id = db_interface.query_account_to_customer(session.customer_id, "customer_id")[0]
        balance = db_interface.query_balance(account_id)[0]
        db_interface.release_lock()
        paket = int_to_bytes(balance)
        send_to_customer(paket, session)
    else:
        error("No customer id to session")


def create_debit_card(customer_id, pin, path):
    debit_card_number = create_number(16)
    debit_card_key = random.bytes(64)
    db_interface.set_up_debit_card(customer_id, debit_card_number, debit_card_key)
    card = debit_card_number.encode(UTF8STR) + encrypt(debit_card_key, hashcode(pin))
    f = open(path, "wb")
    f.write(card)
    f.close()


def customer_routine():
    while True:
        customer_socket_read_lock.acquire()
        paket, src = customer_udp_socket.recvfrom(1024)
        customer_socket_read_lock.release()

        try:
            command = int_from_bytes(paket[0:4])
            if command == LOGIN_COMMAND:
                login(paket[4:], src)
            elif command == BANKING_COMMAND:
                session = session_list.get_session_from_id(paket[4:12], src)
                # session was removed due to logout
                if session is None:
                    continue
                customer_id = session.customer_id
                paket = decrypt(paket[12:], session.session_key)
                banking_command = int_from_bytes(paket[0:4])
                if banking_command == EXIT_COMMAND:
                    user_exit(session)
                elif banking_command == SHOW_BALANCE_COMMAND:
                    show_balance(session)
                elif banking_command == TRANSFER_COMMAND:
                    s = Slice_Iterator(paket, counter=4)
                    transfer_from_session(session, s)
                elif banking_command == SEE_TURNOVER:
                    resume_turnover(customer_id, session)
        except:
            traceback.print_exc()


def card_terminal_routine():
    while True:
        card_terminal_socket_read_lock.acquire()
        paket, src = terminal_udp_socket.recvfrom(1024)
        card_terminal_socket_read_lock.release()
        transfer_from_debit_card(paket)


def routine_server_terminal():
    while True:
        print("Kommandos: 1: SQL-Code eingeben, 2: Konto anlegen, 3: Debitkarte anlegen")
        mode = int(input())
        if mode == 1:
            print("SQL-Code eingeben")
            sql = input()
            try:
                db_interface.acquire_lock()
                res = db_interface.con.execute(sql)
                for x in res:
                    print(x)
            except:
                traceback.print_exc()
            finally:
                db_interface.release_lock()
        elif mode == 2:
            print("Name:")
            name = input()
            print("E-Mail-Adresse:")
            email = input()
            print("Passwort:")
            password = input()
            print("Anfänglicher Kontostand:")
            initial_balance = int(input())
            db_interface.set_up_customer_and_account(name, email, password, initial_balance)
        elif mode == 3:
            print("Kundennummer:")
            customer_id = input()
            print("PIN:")
            pin = input()
            print("Pfad:")
            path = input()
            create_debit_card(customer_id, pin, path)


for i in range(NUMBER_OF_THREADS):
    Thread(target=customer_routine).start()
Thread(target=card_terminal_routine).start()
Thread(target=routine_server_terminal).start()
