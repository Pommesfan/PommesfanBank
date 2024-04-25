class BankService:
    def __init__(self, thread, db_interface, transfer_function, udp_socket, sessionList, ongoing_session_list):
        self._thread = thread
        self._db_interface = db_interface
        self._transfer_function = transfer_function
        self._udp_socket = udp_socket
        self._session_list = sessionList
        self._ongoing_session_list = ongoing_session_list