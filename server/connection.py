import json
from threading import Thread
import sys

class Connection:
    def __init__(self, socket, server):
        self.socket = socket
        self.server = server
        self.authenticated = False
        self.loggedInAs = None

    def start(self):
        thread = Thread(target=self.listen)
        thread.daemon = True
        thread.start() 

    def listen(self):
        try:
            buffer = ""
            while True:
                data = self.socket.recv(4096)
                if not data:
                    break
                buffer += data.decode()
                
                while True:
                    try:
                        message, index = json.JSONDecoder().raw_decode(buffer)
                        buffer = buffer[index:].lstrip()
                        self.server.log(message)
                        self.server.protocol.handleIncoming(self, message)
                    except json.JSONDecodeError:
                        break  # Wait for more data
        except Exception as e:
            print(f"Unkown error: {e}")
        finally: self.close()

    def sendJson(self, outgoing):
        encoded = (json.dumps(outgoing) + "\n").encode()
        self.socket.send(encoded)

    def close(self):
        self.server.log(f"CLOSING:{self.socket}, {self.loggedInAs}")
        self.socket.close()
        sys.exit(0)
        if self in self.server.connections:
            self.server.connections.remove(self)