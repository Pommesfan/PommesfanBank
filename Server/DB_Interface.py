import sqlite3
from threading import Lock


class DB_Interface:
    def __init__(self, url):
        self.con = sqlite3.connect(url, check_same_thread=False)
        self.__lock = Lock()

    def acquire_lock(self):
        self.__lock.acquire()

    def release_lock(self):
        self.__lock.release()

    def close(self):
        self.con.close()

    def init_database(self):
        f = open("Server/SQL-Scripts/create_tables.sql")
        self.con.executescript(f.read())
        self.con.commit()
        self.add_example_customers()

    def add_example_customers(self):
        f = open("Server/SQL-Scripts/create_example_customers.sql")
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
        self.con.commit()
        self.release_lock()

    def transfer(self, transmitter_account_id, target_account_id, new_balance_receiver, new_balance_transmitter,
                 amount, reference):
        self.con.execute("update account set balance = " + str(new_balance_transmitter)
                         + " where account_id = '" + transmitter_account_id + "';")
        self.con.execute("update account set balance = " + str(new_balance_receiver)
                         + " where account_id = '" + target_account_id + "';")
        self.con.execute("insert into transfer values(NULL, '" + transmitter_account_id + "', '" + target_account_id +
                         "', " + str(amount) + ", (select datetime('now', 'localtime')), '" + reference + "', " +
                         str(new_balance_transmitter) + ", " + str(new_balance_receiver) + ");")
        self.con.commit()

    def query_turnover(self, account_id):
        statement = "select c.customer_name, t.account_to, t.amount * -1, t.date, t.reference from transfer t " \
                    "inner join account a on t.account_to = a.account_id inner join customer c on a.customer_id = " \
                    "c.customer_id where t.account_from = '" + account_id + "' union all select c.customer_name, " \
                    "t.account_from, t.amount, t.date, t.reference from transfer t inner join account a on " \
                    "t.account_from = a.account_id inner join customer c on a.customer_id = c.customer_id where " \
                    "t.account_to = '" + account_id + "' order by date desc;"
        res = self.con.execute(statement)
        return res

    def query_customer(self, argument, attribute):
        return self.query_first_item("select * from customer where " + attribute + " = '" + argument + "'")

    def query_balance(self, account_id):
        return self.query_first_item("select balance from account where account_id = '" + account_id + "'")

    def query_customer_name(self, customer_id):
        return self.query_first_item("select customer_name from customer where customer_id = '" + customer_id + "'")

    def query_account_to_customer(self, argument, attribute):
        return self.query_first_item("select account_id from account a inner join customer c on "
                                     "a.customer_id == c.customer_id where c." + attribute + " = '" + argument + "'")
