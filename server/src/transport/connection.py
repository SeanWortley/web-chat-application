import json
from threading import Thread


class Connection:
    def __init__(self, socket, server):
        """
        Initializes a client connection.

        Args:
            socket (socket): The underlying TCP socket.
            server (Server): Reference to the server instance.
        """
        self.socket = socket
        self.server = server
        self.authenticated = False
        self.loggedInAs = None
        self.running = True

    def start(self):
        """
        Starts a background thread to listen for incoming messages.
        """
        thread = Thread(target=self.listen)
        thread.daemon = True
        thread.start()

    def listen(self):
        """
        Receives messages from the client, decodes them, and forwards
        to the server protocol. Cleans up on disconnect or error.
        """
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
                    payload_messages = ["MSG"]
                    if msg_name in payload_messages:
                        if msg_name == "MSG":
                            message["data"]["payload"] = body.decode("utf-8")
                        else:
                            message["data"]["payload"] = body

                self.server.log_incoming(message)
                self.server.protocol.handleIncoming(self, message)

        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            if self.loggedInAs in self.server.active_users:
                self.server.active_users.remove(self.loggedInAs)
            self.close()

    def sendJson(self, outgoing, payload=None):
        """
        Sends a JSON message to the client, optionally including a payload.

        Args:
            outgoing (dict): Message header and data.
            payload (str | bytes, optional): Message body content.
        """
        message_name = outgoing.get("message_name")
        payload_messages = ["MSG"]

        if message_name in payload_messages:
            data = outgoing.get("data")
            payload = data.pop("payload")

        body = (payload or "").encode("utf-8")
        outgoing["length"] = len(body)
        header = json.dumps(outgoing).encode("utf-8")

        self.server.log_outgoing(outgoing)
        self.socket.sendall(header + b"\n" + body)

    def close(self):
        """
        Closes the client connection and removes it from the server.
        """
        self.running = False
        self.server.log(f"CLOSING:{self.socket}, {self.loggedInAs}")
        if hasattr(self, 'socket') and self.socket and not self.socket._closed:
            try:
                self.socket.close()
            except Exception:
                pass
        if self in self.server.connections:
            self.server.connections.remove(self)
