from socket import *
from connection import Connection
from protocol import Protocol

class Client:
    def __init__(self, host, port):
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.connect((host, port))

        self.protocol = Protocol(self)
        self.connection = Connection(self.socket, self)
        self.connection.start()

        self.username = None
        self.authenticated = False


def main():
    client = Client("", 12000)
    client.protocol.AUTH(client.connection)

if __name__ == "__main__":
    main()