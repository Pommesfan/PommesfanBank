import copy
from Crypto.Cipher import AES
from numpy import random as numpy_random
import random
import string

UTF8STR = "utf8"

START_LOGIN = 0
COMPLETE_LOGIN = 1
LOGIN_ACK = 5687789
EXIT_COMMAND = 2
BANKING_COMMAND = 3
SHOW_BALANCE_COMMAND = 4
TRANSFER_COMMAND = 5
SEE_TURNOVER = 6
SHOW_BALANCE_RESPONSE = 7
TRANSFER_ACK = 8
SEE_TURNOVER_RESPONSE = 9
CARD_PAYMENT_COMMAND = 10
INIT_CARD_PAYMENT_COMMAND = 11
EXECUTE_CARD_PAYMENT_COMMAND = 12
PROOF_CARD_PAYMENT_COMMAND = 13
PAYMENT_ORDER_ACK = 14
PAYMENT_EXECUTE_ACK = 15
PAYMENT_EXECUTE_NACK_TRANSFER_CODE = 16
PAYMENT_EXECUTE_NACK_CARDKEY = 17
PAYMENT_EXECUTE_NACK_CARDNUMBER = 18
PAYMENT_PROOF_ACK = 19
PAYMENT_PROOF_NACK = 20

MANUAL_TRANSFER = 1
DEBIT_CARD_PAYMENT = 2


def int_to_bytes(i):
    return int.to_bytes(i, 4, "big", signed=True)


def int_from_bytes(i):
    return int.from_bytes(i, "big", signed=True)


def create_alpha_numeric(len):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=len))


def number_fill_aes_block_to_16x(password_length):
    rest = password_length % 16
    if rest == 0:
        return 0
    else:
        return 16 - rest


def hashcode(v):
    from Crypto.Hash import SHA256
    return SHA256.new(v).digest()


def encrypt_uneven_block(plain, aes):
    return aes.encrypt(plain + numpy_random.bytes(number_fill_aes_block_to_16x(len(plain))))


def get_aes(key):
    aes = AES.new(key, AES.MODE_CBC, b'fhs8d9fg845jskd6')
    return aes, copy.copy(aes)


TERMINATION = int_to_bytes(2147483647)


def create_number(length):
    s = ""
    for i in range(length):
        s += str(numpy_random.randint(0, 10, 1, int)[0])
    return s


class SliceIterator:
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
