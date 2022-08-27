create table customer(customer_id primary key, customer_name, email, password);

create table account(account_id primary key, customer_id, balance, foreign key(customer_id)
references customer(customer_id));

create table transfer(transfer_id integer primary key autoincrement, account_from, account_to, amount, date, reference,
new_balance_transmitter, new_balance_receiver, foreign key(account_from) references account(account_id),
foreign key(account_to) references account(account_id));