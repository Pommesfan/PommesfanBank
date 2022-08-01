class Session:
    def __init__(self, session_id, session_key, customer_id, ip_and_port):
        self.session_id = session_id
        self.session_key = session_key
        self.customer_id = customer_id
        self.ip_and_port = ip_and_port


class SessionList:
    def __init__(self):
        self.__sessions = []

    def add(self, session):
        if isinstance(session, Session):
            self.__sessions.append(session)

    def get_session_from_id(self, session_id, src):
        for s in self.__sessions:
            if s.session_id == session_id and s.ip_and_port == src:
                return s
        return None

    def remove_session(self, session_id):
        for i in range(len(self.__sessions)):
            if self.__sessions[i].session_id == session_id:
                self.__sessions.pop(i)
                return 0
        return -1
