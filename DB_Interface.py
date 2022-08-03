import sqlite3


class DB_Interface:
    def __init__(self, url):
        self.con = sqlite3.connect(url)

    def close(self):
        self.con.close()

    def init_database(self):
        self.con.execute("create table customer(customer_id primary key, customer_name, password, balance);")
        self.con.execute("create table transfer(transfer_id integer primary key autoincrement, customer_from, "
                         "customer_to, amount, date, reference, new_balance_transmitter, new_balance_receiver,"
                         "foreign key(customer_to) references customer(customer_id),"
                         "foreign key(customer_to) references customer(customer_id));")
        self.con.commit()
        self.add_example_customers()

    def add_example_customers(self):
        customers = [
            ("45321695", "AAAA", "hallo", 6598),
            ("15369754", "BBBB", "hi", 9832),
            ("12498625", "CCCC", "ups", 4682),
            ("49871283", "DDDD", "jesses", 361)
        ]
        for c in customers:
            self.con.execute(
                "insert into customer values ('" + c[0] + "', '" + c[1] + "', '" + c[2] + "', " + str(c[3]) + ")")
        self.con.commit()

    def query_first_item(self, sql):
        response = self.con.execute(sql)
        answer = None
        for r in response:
            answer = r
            break
        return answer

    def transfer(self, customer_id, target_customer_id, new_balance_receiver, new_balance_transmitter,
                 amount, reference):
        self.con.execute("update customer set balance = " + str(new_balance_transmitter)
                         + " where customer_id = '" + str(customer_id) + "';")
        self.con.execute("update customer set balance = " + str(new_balance_receiver)
                         + " where customer_id = '" + str(target_customer_id) + "';")
        self.con.execute("insert into transfer values(NULL, '" + customer_id + "', '" + target_customer_id + "', " +
                         str(amount) + ", (select datetime('now', 'localtime')), '" + reference + "', " +
                         str(new_balance_transmitter) + ", " + str(new_balance_receiver) + ");")
        self.con.commit()

    def query_turnover(self, customer_id):
        statement = "select customer_to, amount * -1, date, reference from transfer where customer_from " \
                    "= '" + customer_id + "' union all select customer_from, amount, date, reference from " \
                                          "transfer where customer_to = '" + customer_id + "' order by date desc; "
        res = self.con.execute(statement)
        return res

    def query_customer_by_id(self, customer_id):
        return self.query_first_item("select * from customer where customer_id = '" + customer_id + "'")

    def query_customer_by_name(self, username):
        return self.query_first_item("select * from customer where customer_name = '" + username + "'")

    def query_balance(self, customer_id):
        return self.query_first_item("select balance from customer where customer_id = '" + customer_id + "'")

    def query_customer_name(self, customer_id):
        self.query_first_item("select customer_name from customer where customer_id = '" + customer_id + "'")
