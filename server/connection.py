import json
from threading import Thread

class Connection:
    def __init__(self, socket, server):
        self.socket = socket
        self.server = server
        self.authenticated = False
        self.loggedInAs = None

    def start(self):
        Thread(target=self.listen).start()

    def listen(self):
        while True:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                
                message = json.loads(data.decode())
                self.server.protocol.handleIncoming(self, message)
        
            except Exception as e:
                print(f"Connection error: {e}")
                break

    def sendJson(self, outgoing):
        encoded = json.dumps(outgoing).encode()
        self.socket.send(encoded)

    def close(self):
        self.socket.close()
