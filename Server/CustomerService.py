import socket
import traceback
from Server.BankService import BankService
from Server.Sessions import Session
from Utils import *


class CustomerService(BankService):
    def __init__(self, tcp_port, db_interface, session_list, ongoing_session_list, customer_socket_read_lock,
                 customer_socket_write_lock, udp_socket, localIP, CURRENCY_B, DECIMAL_PLACE_B,
                 transfer_function):
        super().__init__(db_interface, transfer_function, udp_socket, session_list, ongoing_session_list,
                         CURRENCY_B, DECIMAL_PLACE_B, customer_socket_read_lock, customer_socket_write_lock,
                         self.customer_routine)
        self.__tcp_port = tcp_port
        self.__tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__tcp_socket.bind((localIP, tcp_port))
        self.__localIP = localIP

    def get_customer_from_username(self, username):
        self._db_interface.acquire_lock()
        if '@' in username:
            answer = self._db_interface.query_customer(username, "email")
        else:
            answer = self._db_interface.query_customer(username, "customer_id")
        self._db_interface.release_lock()
        return answer

    def __start_login(self, paket, src):
        def query_function(username):
            res = self.get_customer_from_username(username)
            if res is None:
                print("Kundennummer oder E-Mail '" + username + "' nicht registriert")
                return None
            else:
                customer_id = res[0]
                customer_password_b = res[3].encode(UTF8STR)
                return customer_id, customer_password_b

        super().start_login(paket, src, query_function, Session)

    def __complete_login(self, paket, src):
        def query_function(customer_id):
            res = self._db_interface.query_customer(customer_id, "customer_id")
            customer_name = res[1]
            customer_password_b = res[3].encode(UTF8STR)
            return res, customer_name, customer_password_b

        def message_function(user, query_res, success):
            msg = "Login Nutzer: '" + user + "' - '" + query_res[1]
            if success:
                msg += "' erfolgreich"
            else:
                msg += "' nicht erfolgreich"
            print(msg)

        super().complete_login(paket, src, query_function, message_function)

    def transfer_from_session(self, session, slice_iterator):
        receiver_account_len = int_from_bytes(slice_iterator.get_slice(4))
        receiver_account_id = slice_iterator.get_slice(receiver_account_len).decode(UTF8STR)
        amount = int_from_bytes(slice_iterator.get_slice(4))
        reference_length = int_from_bytes(slice_iterator.get_slice(4))
        reference = slice_iterator.get_slice(reference_length).decode(UTF8STR)
        transmitter_account_id = self._db_interface.query_account_to_customer(session.user_id, "customer_id")[0]

        if '@' in receiver_account_id:
            res = self._db_interface.query_account_to_customer(receiver_account_id, "email")
            if res is None:
                return
            receiver_account_id = res[0]

        self._transfer_function(MANUAL_TRANSFER, transmitter_account_id, receiver_account_id, amount, reference)
        self.answer_to_client(session, int_to_bytes(TRANSFER_ACK))

    def tcp_on_demand(self, session):
        paket = int_to_bytes(SEE_TURNOVER_RESPONSE) + int_to_bytes(self.__tcp_port)
        self.answer_to_client(session, paket)
        self.__tcp_socket.listen(1)
        client, _ = self.__tcp_socket.accept()
        return client

    def resume_turnover(self, customer_id, session):
        self._db_interface.acquire_lock()
        account_id = self._db_interface.query_account_to_customer(customer_id, "customer_id")[0]
        res = self._db_interface.query_turnover(account_id)
        client = self.tcp_on_demand(session)

        def overflow_function(b):
            cipher = encrypt_uneven_block(b, session.aes_e)
            client.send(int_to_bytes(len(cipher)))
            client.send(cipher)

        buf = ByteBuffer(1024, overflow_function)

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
            buf.insert(
                transfer_type + transmitter_name_length_b + transmitter_name_b + account_id_b + amount_b + timestamp_b +
                reference_length_b + reference_b)
        buf.insert(TERMINATION)
        buf.flush()
        client.send(int_to_bytes(0))
        self._db_interface.release_lock()
        client.close()

    def user_exit(self, session):
        self._db_interface.acquire_lock()
        name = self._db_interface.query_customer_name(session.user_id)
        self._db_interface.release_lock()
        if self._session_list.remove_session(session.session_id) == -1:
            self.error("remove session: session_id not found")
        print("Nutzer: " + session.user_id + " - " + name[0] + " ausgeloggt")

    def show_balance(self, session):
        if session.user_id is not None:
            self._db_interface.acquire_lock()
            account_id = self._db_interface.query_account_to_customer(session.user_id, "customer_id")[0]
            balance = self._db_interface.query_balance(account_id)[0]
            self._db_interface.release_lock()
            paket = int_to_bytes(SHOW_BALANCE_RESPONSE) + int_to_bytes(balance)
            self.answer_to_client(session, paket)
        else:
            self.error("No customer id to session")

    def customer_routine(self):
        while True:
            self._read_lock.acquire()
            paket, src = self._udp_socket.recvfrom(1024)
            self._read_lock.release()

            try:
                command = int_from_bytes(paket[0:4])
                if command == START_LOGIN:
                    self.__start_login(paket[4:], src)
                elif command == COMPLETE_LOGIN:
                    self.__complete_login(paket[4:], src)
                elif command == BANKING_COMMAND:
                    session = self._session_list.get_session_from_id(paket[4:12], src)
                    # session was removed due to logout
                    if session is None:
                        continue
                    customer_id = session.user_id
                    paket = session.aes_d.decrypt(paket[12:])
                    banking_command = int_from_bytes(paket[0:4])
                    if banking_command == EXIT_COMMAND:
                        self.user_exit(session)
                    elif banking_command == SHOW_BALANCE_COMMAND:
                        self.show_balance(session)
                    elif banking_command == TRANSFER_COMMAND:
                        s = SliceIterator(paket, counter=4)
                        self.transfer_from_session(session, s)
                    elif banking_command == SEE_TURNOVER:
                        self.resume_turnover(customer_id, session)
            except:
                traceback.print_exc()
