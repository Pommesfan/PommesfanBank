--customers
insert into customer values ('45321695', 'Matthias Seehuber', 'matthias.seehuber@gmx.de', 'hallo');
insert into customer values ('15369754', 'Walter Brenz', 'walter.brenz@web.de', 'hi');
insert into customer values ('12498625', 'Zacharias Zorngiebel', 'zacharias.zorngiebel@klever-mail.de', 'ups');
insert into customer values ('49871283', 'Ramona Schön', 'ramona.schoen@yahoo.de', 'jesses');

--accounts
insert into account values ('18697533', '45321695');
insert into account values ('84894692', '15369754');
insert into account values ('57986486', '12498625');
insert into account values ('26684521', '49871283');

insert into daily_closing values(NULL, '18697533', 659836, (select datetime('now', 'localtime')));
insert into daily_closing values(NULL, '84894692', 983284, (select datetime('now', 'localtime')));
insert into daily_closing values(NULL, '57986486', 468215, (select datetime('now', 'localtime')));
insert into daily_closing values(NULL, '26684521', 36187, (select datetime('now', 'localtime')));

--Unternehmenskonto
insert into customer values ('76547564', 'Supermarkt Entenhausen', 'info@supermarkt-entenhausen.de', 'haha');
insert into account values ('98751544', '76547564');
insert into daily_closing values(NULL, '98751544', 4523691, (select datetime('now', 'localtime')));

--Kartenterminal
insert into terminal values('4894d56d4ztr8dt6z7', 'redfg465sdg564er89', '98751544');