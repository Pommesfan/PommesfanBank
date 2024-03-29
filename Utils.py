import numpy

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


def encrypt_uneven_block(plain, aes):
    return aes.encrypt(plain + random.bytes(number_fill_aes_block_to_16x(len(plain))))


def get_aes(key):
    return AES.new(key, AES.MODE_CBC, 'This is an IV456')


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
        return self.__data[c:c + 4] == TERMINATION


class ByteBuffer:
    def __init__(self, size, overflow_function):
        self.__buffer = b''
        self.__buffer_pointer = 0
        self.__overflow_function = overflow_function
        self.__size = size

    def insert(self, chunk):
        chunk_pointer = 0
        while chunk_pointer < len(chunk):
            remaining_buffer_size = self.__size - self.__buffer_pointer
            remaining_chunk_size = len(chunk) - chunk_pointer

            if remaining_chunk_size < remaining_buffer_size:
                self.__buffer += chunk[chunk_pointer:]
                self.__buffer_pointer += (len(chunk) - chunk_pointer)
                return
            else:
                self.__buffer += chunk[chunk_pointer:chunk_pointer + remaining_buffer_size]
                chunk_pointer += remaining_buffer_size
                self.__overflow_function(self.__buffer)
                self.__buffer_pointer = 0
                self.__buffer = b''

    def flush(self):
        self.__overflow_function(self.__buffer[:self.__buffer_pointer])
        self.__buffer_pointer = 0
        self.__buffer = b''
