import socket
import traceback
from DB_Interface import *
from Server.CardTerminalService import CardTerminalService
from Server.CustomerService import CustomerService
from Utils import *
from Sessions import *
from threading import Thread, Lock
from datetime import datetime

NUMBER_OF_THREADS = 4
localIP = "127.0.0.1"
local_port_customer = 20001
local_port_terminal = 20002
firstPortTCP = 20010
CURRENCY_B = "EURO".encode(UTF8STR)
DECIMAL_PLACE_B = int_to_bytes(2)
today = datetime.now().date()
session_list = SessionList()
ongoing_session_list = SessionList()
session_list_card_terminal = SessionList()
ongoing_session_list_card_terminal = SessionList()
db_interface = DB_Interface("./Pommesfan_Bank_DB.db")

card_terminal_socket_write_lock = Lock()


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
    aes_e, aes_d = get_aes(hashcode(pin))
    card = debit_card_number.encode(UTF8STR) + aes_e.encrypt(debit_card_key)
    f = open(path, "wb")
    f.write(card)
    f.close()


def transfer(transfer_type, transmitter_account_id, receiver_account_id, amount, reference):
    timestamp_descriptor = '%Y-%m-%d %H:%M:%S'
    db_interface.acquire_lock()
    daily_closing_transmitter = db_interface.query_daily_closing(transmitter_account_id)
    daily_closing_receiver = db_interface.query_daily_closing(receiver_account_id)
    if daily_closing_receiver is None:
        db_interface.release_lock()
        return
    date_daily_closing_transmitter = datetime.strptime(daily_closing_transmitter[3], timestamp_descriptor)
    date_daily_closing_receiver = datetime.strptime(daily_closing_receiver[3], timestamp_descriptor)
    balance_transmitter = daily_closing_transmitter[2]
    balance_receiver = daily_closing_receiver[2]
    if amount < 1 or transmitter_account_id == receiver_account_id or amount > balance_transmitter:
        db_interface.release_lock()
        return

    # update daily closing for today or create new
    new_balance_receiver = balance_receiver + amount
    new_balance_transmitter = balance_transmitter - amount
    if date_daily_closing_receiver.date() == today:
        db_interface.update_daily_closing(receiver_account_id, new_balance_receiver)
    else:
        db_interface.create_daily_closing(receiver_account_id, new_balance_receiver)
    if date_daily_closing_transmitter.date() == today:
        db_interface.update_daily_closing(transmitter_account_id, new_balance_transmitter)
    else:
        db_interface.create_daily_closing(transmitter_account_id, new_balance_transmitter)
    db_interface.create_transfer(transfer_type, transmitter_account_id, receiver_account_id, new_balance_receiver,
                                 new_balance_transmitter, amount, reference)
    db_interface.release_lock()


if __name__ == '__main__':
    __customer_socket_read_lock = Lock()
    __customer_socket_write_lock = Lock()

    __customer_udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    __customer_udp_socket.bind((localIP, local_port_customer))

    for i in range(NUMBER_OF_THREADS):
        CustomerService(
            firstPortTCP + i,
            db_interface,
            session_list,
            ongoing_session_list,
            __customer_socket_read_lock,
            __customer_socket_write_lock,
            __customer_udp_socket,
            localIP,
            CURRENCY_B,
            DECIMAL_PLACE_B,
            transfer
        ).start()

    terminal_udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    terminal_udp_socket.bind((localIP, local_port_terminal))
    card_terminal_socket_read_lock = Lock()

    CardTerminalService(db_interface, transfer, terminal_udp_socket, card_terminal_socket_read_lock,
                        card_terminal_socket_write_lock, session_list_card_terminal, ongoing_session_list, CURRENCY_B,
                        DECIMAL_PLACE_B).start()
    Thread(target=routine_server_terminal).start()
