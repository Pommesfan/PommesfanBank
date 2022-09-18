from Crypto.Cipher import AES
from numpy import random

UTF8STR = "utf8"

LOGIN_COMMAND = 0
EXIT_COMMAND = 1
BANKING_COMMAND = 2
SHOW_BALANCE_COMMAND = 3
TRANSFER_COMMAND = 4
SEE_TURNOVER = 5

MANUAL_TRANSFER = 1
DEBIT_CARD_PAYMENT = 2


def int_to_bytes(i):
    return int.to_bytes(i, 4, "big", signed=True)


def int_from_bytes(i):
    return int.from_bytes(i, "big", signed=True)


def number_fill_aes_block_to_16x(password_length):
    rest = password_length % 16
    if rest == 0:
        return 0
    else:
        return 16 - rest


def hashcode(v):
    from Crypto.Hash import SHA256
    return SHA256.new(v.encode(UTF8STR)).digest()


def encrypt(plain, key):
    obj1 = AES.new(key, AES.MODE_CBC, 'This is an IV456')
    return obj1.encrypt(plain + random.bytes(number_fill_aes_block_to_16x(len(plain))))


def decrypt(cipher, key):
    aes = AES.new(key, AES.MODE_CBC, 'This is an IV456')
    return aes.decrypt(cipher)


def split_pakets(big_paket, send_function, paket_len):
    number_of_full_pakets = int(len(big_paket) / paket_len)
    size_of_last_paket = len(big_paket) % paket_len
    initial_paket = int_to_bytes(number_of_full_pakets) + int_to_bytes(size_of_last_paket)
    send_function(initial_paket)
    for i in range(number_of_full_pakets):
        paket = big_paket[i * paket_len: (i + 1) * paket_len]
        send_function(paket)

    last_paket = big_paket[number_of_full_pakets * paket_len:]
    if len(last_paket) != 0:
        send_function(last_paket)


def unite_pakets(paket_len, udp_socket, session_key):
    initial_paket = decrypt(udp_socket.recv(16), session_key)
    number_of_full_pakets = int_from_bytes(initial_paket[0:4])
    size_of_last_paket = int_from_bytes(initial_paket[4:8])
    b = b''
    for i in range(number_of_full_pakets):
        paket = udp_socket.recv(paket_len)
        b += (decrypt(paket, session_key))
    if size_of_last_paket != 0:
        paket = udp_socket.recv(size_of_last_paket + number_fill_aes_block_to_16x(size_of_last_paket))
        b += (decrypt(paket, session_key))
    return b


TERMINATION = int_to_bytes(2147483647)


def create_number(length):
    s = ""
    for i in range(length):
        s += str(random.randint(0, 10, 1, int)[0])
    return s


class Slice_Iterator:
    def __init__(self, data, counter=0):
        self.__counter = counter
        self.__data = data

    def get_slice(self, length):
        start = self.__counter
        end = start + length
        self.__counter = end
        return self.__data[start:end]

    def get_int(self):
        return int_from_bytes(self.get_slice(4))

    def next_slice(self):
        return self.get_slice(self.get_int())

    def end_reached(self):
        c = self.__counter
        return self.__data[c:c+4] == TERMINATION
