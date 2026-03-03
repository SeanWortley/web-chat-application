from ast import main
from socket import *
import json
from hashlib import sha256
import time
from connection import Connection
from protocol import Protocol


class Server:
    userList = {"username": sha256("password".encode()).hexdigest(), "admin": sha256("admin".encode()).hexdigest()}

    def __init__(self, host, port):
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.protocol = Protocol(self)
        self.socket.listen()

    def listen(self):
        while True:
            clientSocket, address = self.socket.accept()

            connection = Connection(clientSocket, self)
            connection.start()


def main():
    server = Server("", 12000)
    server.listen()


if __name__ == "__main__":
    main()