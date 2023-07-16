import socket
import traceback
from DB_Interface import *
from Server.CustomerService import CustomerService
from Utils import *
from Sessions import *
from threading import Thread, Lock

NUMBER_OF_THREADS = 4
localIP = "127.0.0.1"
local_port_customer = 20001
local_port_terminal = 20002
firstPortTCP = 20010
CURRENCY_B = "EURO".encode(UTF8STR)
DECIMAL_PLACE_B = int_to_bytes(2)

terminal_udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
terminal_udp_socket.bind((localIP, local_port_terminal))

card_terminal_socket_read_lock = Lock()
card_terminal_socket_write_lock = Lock()

session_list = SessionList()
db_interface = DB_Interface("./Pommesfan_Bank_DB.db")


def transfer_from_debit_card(paket):
    s = Slice_Iterator(paket)
    terminal_id = s.next_slice().decode(UTF8STR)
    terminal = db_interface.query_terminal(terminal_id)

    if terminal is None:
        return

    terminal_key = terminal[1]
    account_to = terminal[2]

    cipher_paket = s.next_slice()
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
    amount = s.get_int()
    reference = s.next_slice().decode(UTF8STR)

    transfer(DEBIT_CARD_PAYMENT, account_from, account_to, amount, reference)


def card_terminal_routine():
    while True:
        try:
            card_terminal_socket_read_lock.acquire()
            paket, src = terminal_udp_socket.recvfrom(1024)
            card_terminal_socket_read_lock.release()
            transfer_from_debit_card(paket)
        except:
            traceback.print_exc()


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


def create_debit_card(customer_id, pin, path):
    debit_card_number = create_number(16)
    debit_card_key = random.bytes(64)
    db_interface.set_up_debit_card(customer_id, debit_card_number, debit_card_key)
    card = debit_card_number.encode(UTF8STR) + encrypt(debit_card_key, hashcode(pin))
    f = open(path, "wb")
    f.write(card)
    f.close()


def transfer(transfer_type, transmitter_account_id, receiver_account_id, amount, reference):
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
    db_interface.transfer(transfer_type, transmitter_account_id, receiver_account_id, new_balance_receiver,
                          new_balance_transmitter, amount, reference)
    db_interface.release_lock()


if __name__ == '__main__':
    __customer_socket_read_lock = Lock()
    __customer_socket_write_lock = Lock()

    __customer_udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    __customer_udp_socket.bind((localIP, local_port_customer))

    for i in range(NUMBER_OF_THREADS):
        CustomerService(
            i,
            db_interface,
            session_list,
            __customer_socket_read_lock,
            __customer_socket_write_lock,
            __customer_udp_socket,
            localIP,
            firstPortTCP,
            CURRENCY_B,
            DECIMAL_PLACE_B,
            transfer
        ).start()
    Thread(target=card_terminal_routine).start()
    Thread(target=routine_server_terminal).start()
