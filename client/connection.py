import json
from queue import Queue
from threading import Thread

class Connection:
    def __init__(self, socket, client):
        self.client = client
        self.socket = socket

    def start(self):
        Thread(target=self.listen).start()

    def listen(self):
        try:
            while True:
                data = self.socket.recv(1024)
                if not data:
                    break
                
                message = json.loads(data.decode())
                self.client.protocol.handleIncoming(self, message)
        except Exception as e:
            if not self.socket._closed:
                print(f"Connection error: {e}")
        finally:
            self.close()

    def sendJson(self, outgoing):
        encoded = json.dumps(outgoing).encode()
        self.socket.send(encoded)

    def close(self):
        if not self.socket._closed:
            self.socket.close()