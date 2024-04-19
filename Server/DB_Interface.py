import os.path
import sqlite3
from threading import Lock


class DB_Interface:
    def __init__(self, url):
        is_new = not os.path.isfile(url)
        self.con = sqlite3.connect(url, check_same_thread=False)
        if is_new:
            self.__init_database__()
        self.__lock = Lock()

    def acquire_lock(self):
        self.__lock.acquire()

    def release_lock(self):
        self.__lock.release()

    def close(self):
        self.con.close()

    def __init_database__(self):
        f = open("/home/johannes/Programming/PommesfanBank/Server/SQL-Scripts/create_tables.sql")
        self.con.executescript(f.read())
        self.con.commit()
        self.add_example_customers()

    def add_example_customers(self):
        f = open("/home/johannes/Programming/PommesfanBank/Server/SQL-Scripts/create_example_customers.sql")
        self.con.executescript(f.read())
        self.con.commit()

    def query_first_item(self, sql):
        response = self.con.execute(sql)
        answer = None
        for r in response:
            answer = r
            break
        return answer

    def set_up_customer_and_account(self, name, email, password, balance):
        from Utils import create_number
        customer_id = create_number(8)
        account_id = create_number(8)
        self.acquire_lock()
        self.con.execute("insert into customer values ('" + customer_id + "', '" + name + "', '" + email +
                         "', '" + password + "');")
        self.con.execute("insert into account values ('" + account_id + "', '" + customer_id + "', " + str(balance) +
                         ");")
        self.release_lock()

    def set_up_debit_card(self, customer_id, debit_card_number, debit_card_key):
        self.acquire_lock()
        self.con.execute("insert into debit_card values('" + debit_card_number + "', ?, '"
                         + customer_id + "');", (sqlite3.Binary(debit_card_key),))
        self.con.commit()
        self.release_lock()

    def create_transfer(self, transfer_type, transmitter_account_id, target_account_id, new_balance_receiver,
                        new_balance_transmitter, amount, reference):
        self.con.execute("insert into transfer values(NULL, '" + str(transfer_type) + "', '" + transmitter_account_id +
                         "', '" + target_account_id + "', " + str(amount) + ", (select datetime('now', 'localtime')), '"
                         + reference + "');")
        self.con.commit()

    def query_turnover(self, account_id):
        statement = """select t.transfer_type, c.customer_name, t.account_to, t.amount * -1, t.date, t.reference from 
                    transfer t inner join account a on t.account_to = a.account_id inner join customer c on 
                    a.customer_id = c.customer_id where t.account_from = ? union all select 
                    t.transfer_type, c.customer_name, t.account_from, t.amount, t.date, t.reference from transfer t 
                    inner join account a on t.account_from = a.account_id inner join customer c on a.customer_id = 
                    c.customer_id where t.account_to = ? order by date desc;"""
        return self.con.execute(statement, (account_id, account_id))

    def query_customer(self, argument, attribute):
        return self.query_first_item("select * from customer where " + attribute + " = '" + argument + "'")

    def query_balance(self, account_id):
        return self.query_first_item("select balance from daily_closing where account_id = '" + account_id +
                                     "' order by date desc")

    def query_daily_closing(self, account_id):
        return self.query_first_item("select * from daily_closing where account_id = '" + account_id + "'")

    def query_customer_name(self, customer_id):
        return self.query_first_item("select customer_name from customer where customer_id = '" + customer_id + "'")

    def query_account_to_customer(self, argument, attribute):
        return self.query_first_item("select account_id from account a inner join customer c on "
                                     "a.customer_id == c.customer_id where c." + attribute + " = '" + argument + "'")

    def query_terminal(self, terminal_id):
        return self.query_first_item("select * from terminal where terminal_id = '" + terminal_id + "';")

    def query_account_to_card(self, card_number):
        return self.query_first_item("""select a.account_id, d.card_key from debit_card d inner join account a on
        d.customer_id = a.customer_id where d.card_number = '""" + card_number + "';")

    def create_daily_closing(self, account_id, new_balance):
        self.con.execute("""insert into daily_closing values(NULL, ?, ?,(select datetime('now', 'localtime')))""",
                         (account_id, new_balance))

    def update_daily_closing(self, account_id, new_balance):
        self.con.execute("update daily_closing set balance = " + str(new_balance)
                         + " where account_id = '" + account_id + "';")
