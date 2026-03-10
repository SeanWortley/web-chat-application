import json
from queue import Queue
from threading import Thread
import socket
import traceback

class Connection:
    def __init__(self, socket, client):
        self.client = client
        self.socket = socket
        self.running = True

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
                        if self.client and hasattr(self.client, 'protocol'):
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
        self.running = False
        if hasattr(self, 'socket') and self.socket and not self.socket._closed:
            try:
                self.socket.close()
            except Exception as e:
                pass
            
