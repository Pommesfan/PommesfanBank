UTF8STR = "utf8"


def int_to_bytes(i):
    return int.to_bytes(i, 4, "big")


def int_from_bytes(i):
    return int.from_bytes(i, "big")
