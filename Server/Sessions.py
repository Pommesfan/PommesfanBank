from threading import Lock

import Server.Sessions


class Session:
    def __init__(self, session_id, session_key, customer_id, ip_and_port, aes):
        self.session_id = session_id
        self.session_key = session_key
        self.customer_id = customer_id
        self.ip_and_port = ip_and_port
        self.aes = aes


class SessionList:
    def __init__(self):
        self.__sessions = []
        self.__lock = Lock()

    def add(self, session):
        if isinstance(session, Server.Sessions.Session):
            session_with_same_customer = self.get_session_to_customer(session.customer_id)
            self.__lock.acquire()
            if session_with_same_customer is not None:
                self.__sessions[session_with_same_customer] = session
            else:
                self.__sessions.append(session)
            self.__lock.release()

    def get_session_from_id(self, session_id, src):
        self.__lock.acquire()
        for s in self.__sessions:
            if s.session_id == session_id and s.ip_and_port == src:
                self.__lock.release()
                return s
        self.__lock.release()
        return None

    def remove_session(self, session_id):
        self.__lock.acquire()
        for i in range(len(self.__sessions)):
            if self.__sessions[i].session_id == session_id:
                self.__sessions.pop(i)
                self.__lock.release()
                return 0
        self.__lock.release()
        return -1

    def get_session_to_customer(self, customer_id):
        self.__lock.acquire()
        for i in range(len(self.__sessions)):
            if self.__sessions[i].customer_id == customer_id:
                self.__lock.release()
                return i
        self.__lock.release()
        return None
