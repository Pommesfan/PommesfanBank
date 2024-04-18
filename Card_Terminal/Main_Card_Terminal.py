import socket
from Utils import *

terminal_id_b = '4894d56d4ztr8dt6z7'.encode(UTF8STR)
terminal_key = 'redfg465sdg564er89'

serverIP = "127.0.0.1"
serverPort = 20002

dst = (serverIP, serverPort)
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

aes_terminal_e, aes_terminal_d = get_aes(hashcode(terminal_key))


def send_to_server(paket):
    cipher_paket = encrypt_uneven_block(paket, aes_terminal_e)
    UDPClientSocket.sendto(
        int_to_bytes(len(terminal_id_b)) + terminal_id_b + int_to_bytes(len(cipher_paket)) + cipher_paket, dst)


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

paket = card_id_b + card_key + amount_b + len_refenrence_b + reference_b
send_to_server(paket)
