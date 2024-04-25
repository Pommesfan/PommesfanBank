import socket
from Utils import *

terminal_id_b = '4894d56d4ztr8dt6z7'.encode(UTF8STR)
terminal_key_b = b'redfg465sdg564er89'

serverIP = "127.0.0.1"
serverPort = 20002

dst = (serverIP, serverPort)
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

aes_terminal_e, aes_terminal_d = get_aes(hashcode(terminal_key_b))


def send_to_server(paket):
    cipher_paket = encrypt_uneven_block(paket, aes_terminal_e)
    UDPClientSocket.sendto(
        int_to_bytes(len(terminal_id_b)) + terminal_id_b + int_to_bytes(len(cipher_paket)) + cipher_paket, dst)


def login():
    # start login paket
    password_hash = hashcode(terminal_key_b)
    aes_from_password_e, aes_from_password_d = get_aes(password_hash)
    paket = int_to_bytes(START_LOGIN) + int_to_bytes(len(terminal_id_b)) + terminal_id_b
    UDPClientSocket.sendto(paket, dst)

    # receive start login response
    paket = UDPClientSocket.recv(96)
    s = Slice_Iterator(paket)
    bank_information = s.next_slice()
    session_id = s.get_slice(8)
    session_key = aes_from_password_d.decrypt(s.get_slice(32))
    aes_e, aes_d = get_aes(session_key)

    # complete login
    password_cipher = encrypt_uneven_block(int_to_bytes(len(terminal_key_b)) + terminal_key_b, aes_e)
    paket = int_to_bytes(COMPLETE_LOGIN) + session_id + int_to_bytes(len(password_cipher)) + password_cipher
    UDPClientSocket.sendto(paket, dst)

    ack = int_from_bytes(UDPClientSocket.recv(4))
    if ack != LOGIN_ACK:
        exit(1)
    return bank_information, session_id, aes_e, aes_d


print("Pfad Karte:")
f = open(input(), "rb")
card = f.read(80)
card_id_b = card[:16]
card_key_cipher = card[16:80]
print("PIN:")
pin = input()
aes_pin_e, aes_pin_d = get_aes(hashcode(pin))
card_key = aes_pin_d.decrypt(card_key_cipher)
print("Preis:")

amount_b = int_to_bytes(int(input()))
print("Verwendungszweck:")
reference_b = input().encode(UTF8STR)
len_refenrence_b = int_to_bytes(len(reference_b))

bank_information, session_id, aes_e, aes_d = login()

paket = card_id_b + card_key + amount_b + len_refenrence_b + reference_b
send_to_server(paket)
