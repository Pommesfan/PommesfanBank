import sqlite3
from threading import Lock


class DB_Interface:
    def __init__(self, url):
        self.con = sqlite3.connect(url, check_same_thread=False)
        self.__lock = Lock()

    def acquire_lock(self):
        self.__lock.acquire()
        pass

    def release_lock(self):
        self.__lock.release()
        pass

    def close(self):
        self.con.close()

    def init_database(self):
        self.con.execute("create table customer(customer_id primary key, customer_name, email, password);")
        self.con.execute("create table account(account_id primary key, customer_id, balance,"
                         "foreign key(customer_id) references customer(customer_id));")
        self.con.execute("create table transfer(transfer_id integer primary key autoincrement, account_from, "
                         "account_to, amount, date, reference, new_balance_transmitter, new_balance_receiver,"
                         "foreign key(account_from) references account(account_id),"
                         "foreign key(account_to) references account(account_id));")
        self.con.commit()
        self.add_example_customers()

    def add_example_customers(self):
        customers = [
            ("45321695", "Matthias Seehuber", "matthias.seehuber@gmx.de", "hallo"),
            ("15369754", "Walter Brenz", "walter.brenz@web.de", "hi"),
            ("12498625", "Zacharias Zorngiebel", "zacharias.zorngiebel@klever-mail.de", "ups"),
            ("49871283", "Ramona Schön", "ramona.schoen@yahoo.de", "jesses")
        ]
        accounts = [
            ("18697533", "45321695", 6598),
            ("84894692", "15369754", 9832),
            ("57986486", "12498625", 4682),
            ("26684521", "49871283", 361),
        ]
        for c in customers:
            self.con.execute(
                "insert into customer values ('" + c[0] + "', '" + c[1] + "', '" + c[2] + "', '" + c[3] + "');")
        for a in accounts:
            self.con.execute(
                "insert into account values ('" + a[0] + "', '" + a[1] + "', " + str(a[2]) + ");")

        self.con.commit()

    def query_first_item(self, sql):
        response = self.con.execute(sql)
        answer = None
        for r in response:
            answer = r
            break
        return answer

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

    def query_customer_by_id(self, customer_id):
        return self.query_first_item("select * from customer where customer_id = '" + customer_id + "'")

    def query_customer_by_name(self, username):
        return self.query_first_item("select * from customer where customer_name = '" + username + "'")

    def query_balance(self, account_id):
        return self.query_first_item("select balance from account where account_id = '" + account_id + "'")

    def query_customer_name(self, customer_id):
        return self.query_first_item("select customer_name from customer where customer_id = '" + customer_id + "'")

    def query_account_to_customer(self, customer_id):
        return self.query_first_item("select account_id from account a inner join customer c on "
                                     "a.customer_id == c.customer_id where c.customer_id = '" + customer_id + "'")
