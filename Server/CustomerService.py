import socket
import traceback
from threading import Thread
from Server.Sessions import Session
from Utils import *


class CustomerService:
    def __init__(self, tcp_port, dbInterface, sessionList, customer_socket_read_lock, customer_socket_write_lock,
                 customer_udp_socket, localIP, CURRENCY_B, DECIMAL_PLACE_B, transfer_function):
        self.__tcp_port = tcp_port
        self.__tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__tcp_socket.bind((localIP, tcp_port))
        self.__thread = Thread(target=self.customer_routine)
        self.__db_interface = dbInterface
        self.__session_list = sessionList
        self.__customer_socket_read_lock = customer_socket_read_lock
        self.__customer_socket_write_lock = customer_socket_write_lock
        self.__customer_udp_socket = customer_udp_socket
        self.__localIP = localIP
        self.__CURRENCY_B = CURRENCY_B
        self.__DECIMAL_PLACE_B = DECIMAL_PLACE_B
        self.__transfer_function = transfer_function

    def start(self):
        self.__thread.start()

    def send_to_customer(self, paket, session):
        cipher_paket = encrypt(paket, session.session_key)
        self.__customer_socket_write_lock.acquire()
        self.__customer_udp_socket.sendto(cipher_paket, session.ip_and_port)
        self.__customer_socket_write_lock.release()

    def error(self, s):
        self.__db_interface.acquire_lock()
        self.__db_interface.close()
        self.__db_interface.release_lock()
        print(s)
        exit(1)

    def get_customer_from_username(self, username, input_password_cipher, length_of_password):
        self.__db_interface.acquire_lock()
        if '@' in username:
            answer = self.__db_interface.query_customer(username, "email")
        else:
            answer = self.__db_interface.query_customer(username, "customer_id")
        self.__db_interface.release_lock()

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

    def login(self, paket, src):
        s = Slice_Iterator(paket)
        username = s.next_slice().decode(UTF8STR)
        length_of_password = int_from_bytes(s.get_slice(4))
        password_cipher = s.get_slice(length_of_password + number_fill_aes_block_to_16x(length_of_password))

        res = self.get_customer_from_username(username, password_cipher, length_of_password)
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
            self.__session_list.add(Session(session_id, session_key, customer_id, src))
            bank_information = int_to_bytes(len(self.__CURRENCY_B)) + self.__CURRENCY_B + self.__DECIMAL_PLACE_B

            self.__customer_socket_write_lock.acquire()
            self.__customer_udp_socket.sendto(session_id + session_key_cipher + bank_information, src)
            self.__customer_socket_write_lock.release()

    def transfer_from_session(self, session, slice_iterator):
        receiver_account_len = int_from_bytes(slice_iterator.get_slice(4))
        receiver_account_id = slice_iterator.get_slice(receiver_account_len).decode(UTF8STR)
        amount = int_from_bytes(slice_iterator.get_slice(4))
        reference_length = int_from_bytes(slice_iterator.get_slice(4))
        reference = slice_iterator.get_slice(reference_length).decode(UTF8STR)
        transmitter_account_id = self.__db_interface.query_account_to_customer(session.customer_id, "customer_id")[0]

        if '@' in receiver_account_id:
            res = self.__db_interface.query_account_to_customer(receiver_account_id, "email")
            if res is None:
                return
            receiver_account_id = res[0]

        self.__transfer_function(MANUAL_TRANSFER, transmitter_account_id, receiver_account_id, amount, reference)

    def tcp_on_demand(self, session):
        self.send_to_customer(int_to_bytes(self.__tcp_port), session)
        self.__tcp_socket.listen(1)
        client, _ = self.__tcp_socket.accept()
        return client

    def resume_turnover(self, customer_id, session):
        self.__db_interface.acquire_lock()
        account_id = self.__db_interface.query_account_to_customer(customer_id, "customer_id")[0]
        res = self.__db_interface.query_turnover(account_id)
        # make large bytes array of all information
        b = b''
        for x in res:
            reference = x[5]
            transfer_type = int_to_bytes(x[0])
            transmitter_name_b = x[1].encode(UTF8STR)
            account_id_b = x[2].encode(UTF8STR)
            amount_b = int_to_bytes(x[3])
            timestamp_b = x[4].encode(UTF8STR)
            transmitter_name_length_b = int_to_bytes(len(transmitter_name_b))
            reference_b = reference.encode(UTF8STR)
            reference_length_b = int_to_bytes(len(reference_b))
            b += (
                    transfer_type + transmitter_name_length_b + transmitter_name_b + account_id_b + amount_b + timestamp_b +
                    reference_length_b + reference_b)
        b += TERMINATION
        self.__db_interface.release_lock()

        client = self.tcp_on_demand(session)
        client.send(int_to_bytes(len(b)))
        client.send(b)
        client.close()

    def user_exit(self, session):
        self.__db_interface.acquire_lock()
        name = self.__db_interface.query_customer_name(session.customer_id)
        self.__db_interface.release_lock()
        if self.__session_list.remove_session(session.session_id) == -1:
            self.error("remove session: session_id not found")
        print("Nutzer: " + session.customer_id + " - " + name[0] + " ausgeloggt")

    def show_balance(self, session):
        if session.customer_id is not None:
            self.__db_interface.acquire_lock()
            account_id = self.__db_interface.query_account_to_customer(session.customer_id, "customer_id")[0]
            balance = self.__db_interface.query_balance(account_id)[0]
            self.__db_interface.release_lock()
            paket = int_to_bytes(balance)
            self.send_to_customer(paket, session)
        else:
            self.error("No customer id to session")

    def customer_routine(self):
        while True:
            self.__customer_socket_read_lock.acquire()
            paket, src = self.__customer_udp_socket.recvfrom(1024)
            self.__customer_socket_read_lock.release()

            try:
                command = int_from_bytes(paket[0:4])
                if command == LOGIN_COMMAND:
                    self.login(paket[4:], src)
                elif command == BANKING_COMMAND:
                    session = self.__session_list.get_session_from_id(paket[4:12], src)
                    # session was removed due to logout
                    if session is None:
                        continue
                    customer_id = session.customer_id
                    paket = decrypt(paket[12:], session.session_key)
                    banking_command = int_from_bytes(paket[0:4])
                    if banking_command == EXIT_COMMAND:
                        self.user_exit(session)
                    elif banking_command == SHOW_BALANCE_COMMAND:
                        self.show_balance(session)
                    elif banking_command == TRANSFER_COMMAND:
                        s = Slice_Iterator(paket, counter=4)
                        self.transfer_from_session(session, s)
                    elif banking_command == SEE_TURNOVER:
                        self.resume_turnover(customer_id, session)
            except:
                traceback.print_exc()
