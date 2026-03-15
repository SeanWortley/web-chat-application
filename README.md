# Run from project root

## Server:
### Default Localhost:
python3 server/main.py

### Specify Ip And Port
python3 server/main.py --host {hostip} --port {hostport}

### Server Clean Runtime DB (Does Not Start Server):
python3 server/main.py --clean

## Client:
### Default Localhost And GUI:
python3 client/main.py

### Specify Ip, Port And/Or Terminal:
python3 client/main.py --host {hostip} --port {hostport} --terminal

### Client Clean Runtime DB And Any Temp .bin Files:
python3 client/main.py --clean
