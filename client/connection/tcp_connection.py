import json
from queue import Queue
from threading import Thread
import socket
import traceback

class TCPConnection:
    def __init__(self, socket, client):
        self.client = client
        self.socket = socket
        self.running = True

    def start(self):
        thread = Thread(target=self.listen)
        thread.daemon = True
        thread.start()

    def listen(self):
        try:
            buffer = b""
            while True:
                while b"\n" not in buffer:
                    chunk = self.socket.recv(1024)
                    if not chunk:
                        return
                    buffer += chunk

                header, buffer = buffer.split(b"\n", 1)
                message = json.loads(header.decode("utf-8"))
                
                if "length" in message:
                    length = message.get("length")
                    while len(buffer) < length:
                        chunk = self.socket.recv(1024)
                        if not chunk:
                            return
                        buffer += chunk
                    
                    body = buffer[:length]
                    buffer = buffer[length:]

                    msg_name = message.get("message_name")
                    payload_messages = ["MSG"] # Add media stuff here later
                    if msg_name in payload_messages:
                        if msg_name == "MSG":
                            message["data"]["payload"] = body.decode("utf-8")
                        else:
                            message["data"]["payload"] = body  # raw bytes for media

                self.client.protocol.handleIncoming(self, message)

        except Exception as e:
            print(f"TCPConnection error: {e}")
        finally:
            self.close()

    def sendJson(self, outgoing, payload=None):
        # Payload is inside header... whoops
        message_name = outgoing.get("message_name")
        payload_messages = ["MSG"] # Add media stuff here later

        if (message_name in payload_messages):
            data = outgoing.get("data")
            payload = data.pop("payload")

        body = (payload or "").encode("utf-8")
        outgoing["length"] = len(body)
        header = json.dumps(outgoing).encode("utf-8")
        
        self.socket.sendall(header + b"\n" + body)



    

    def close(self): 
        self.running = False
        if hasattr(self, 'socket') and self.socket and not self.socket._closed:
            try:
                self.socket.close()
            except Exception as e:
                pass
            
