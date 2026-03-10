import json
from threading import Thread

class Connection:
    def __init__(self, socket, server):
        self.socket = socket
        self.server = server
        self.authenticated = False
        self.loggedInAs = None
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
                        print(message)
                        self.server.protocol.handleIncoming(self, message)
                    except json.JSONDecodeError:
                        break  # Wait for more data
                    except Exception as e:
                            if self.running:  # Only log if not intentionally closed
                                print(f"Error in connection listen: {e}")
                            break
        except Exception as e:
            print(f"Unkown error: {e}")
        finally: self.close()

    def sendJson(self, outgoing):
        encoded = (json.dumps(outgoing) + "\n").encode()
        self.socket.send(encoded)

    def close(self):
        self.running = False
        if hasattr(self, 'socket') and self.socket and not self.socket._closed:
            try:
                self.socket.close()
            except:
                pass
        
        if self in self.server.connections:
            self.server.connections.remove(self)
            if self.loggedInAs:
                print(f"User {self.loggedInAs} disconnected")
