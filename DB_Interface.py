import sqlite3


class DB_Interface:
    def __init__(self, url):
        self.con = sqlite3.connect(url)

    def close(self):
        self.con.close()

    def init_database(self):
        self.con.execute("create table customer(customer_id, customer_name, password, balance)")
        self.con.commit()

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

    def transfer(self, customer_id, target_customer_id, new_balance_receiver, new_balance_transmitter):
        self.con.execute("update customer set balance = " + str(new_balance_transmitter)
                         + " where customer_id = '" + str(customer_id) + "';")
        self.con.execute("update customer set balance = " + str(new_balance_receiver)
                         + " where customer_id = '" + str(target_customer_id) + "';")
        self.con.commit()
