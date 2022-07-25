from Crypto.Cipher import AES
from numpy import random

UTF8STR = "utf8"

LOGIN_COMMAND = 0
BANKING_COMMAND = 1
SHOW_BALANCE_COMMAND = 2
TRANSFER_COMMAND = 3


def int_to_bytes(i):
    return int.to_bytes(i, 4, "big")


def int_from_bytes(i):
    return int.from_bytes(i, "big")


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
