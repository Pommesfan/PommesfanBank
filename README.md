# PommesfanBank
for fun, I program my own banking software which works with pseudo money.


Docker Commands(in git bash):


docker build -t pommesfan_bank_client -f Dockerfile_Client .

docker build -t pommesfan_bank_server -f Dockerfile_Server .


docker run -i --network=host pommesfan_bank_server

docker run -i --network=host pommesfan_bank_client
