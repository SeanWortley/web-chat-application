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
        try:
            while True:
                data = self.socket.recv(1024)
                if not data:
                    break
                message = json.loads(data.decode())
                print(message)
                self.server.protocol.handleIncoming(self, message)
        
        except Exception as e:
            print(f"Unkown error: {e}")
        finally: self.close()

    def sendJson(self, outgoing):
        encoded = json.dumps(outgoing).encode()
        self.socket.send(encoded)

    def close(self):
        print(f"CLOSING:{self.socket}, {self.loggedInAs}")
        self.socket.close()
        if self in self.server.connections:
            self.server.connections.remove(self)
