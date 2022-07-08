UTF8STR = "utf8"

LOGIN_COMMAND = 0
SHOW_BALANCE_COMMAND = 1
TRANSFER_COMMAND = 2


def int_to_bytes(i):
    return int.to_bytes(i, 4, "big")


def int_from_bytes(i):
    return int.from_bytes(i, "big")
