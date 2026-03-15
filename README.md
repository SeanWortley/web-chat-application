# Run from project root

##Server:
###Default Localhost:
python3 server/main.py

###Specify ip and port
python3 server/main.py --host {hostip} --port {hostport}

###Server clean runtime DB (Does not start server):
python3 server/main.py --clean

##Client:
###Default Localhost and GUI:
python3 client/main.py

###Specify ip, port and/or terminal:
python3 client/main.py --host {hostip} --port {hostport} --terminal

###Client clean runtime DB and any temp .bin files (left behind if media transfer is cut midway, does not start client):
python3 client/main.py --clean
