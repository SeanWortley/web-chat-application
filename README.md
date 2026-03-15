Run from project root

Server:
python3 server/main.py --host {hostip} --port {hostport}

Server clean runtime DB:
python3 server/main.py --clean

Client (GUI):
python3 client/main.py --host {hostip} --port {hostport}

Client (Terminal):
python3 client/main.py --host {hostip} --port {hostport} --terminal

Client clean runtime DB and any temp .bin files (left behind if media transfer is cut midway):
python3 client/main.py --clean
