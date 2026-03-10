import json
from queue import Queue
from threading import Thread
import socket
import traceback

class Connection:
    def __init__(self, socket, client):
        self.client = client
        self.socket = socket

    def start(self):
        Thread(target=self.listen).start()

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
                        self.client.protocol.handleIncoming(self, message)
                    except json.JSONDecodeError:
                        break  # Wait for more data
        except Exception as e:
            if not self.socket._closed:
                print(f"Connection error: {e}")
        finally:
            self.close()

    def sendJson(self, outgoing):
        encoded = (json.dumps(outgoing)+"\n").encode()
        self.socket.send(encoded)

    

    def close(self): 
        if not self.socket._closed: 
            import traceback 
            traceback.print_stack() 
            self.socket.close()
