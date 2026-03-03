from ast import main
from socket import *
import json
from hashlib import sha256
import time
from connection import Connection


class Server:
    userList = {"username": sha256("password".encode()).hexdigest(), "admin": sha256("admin".encode()).hexdigest()}

    def __init__(self, host, port):
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.socket.listen()

    def listen(self):
        while True:
            clientSocket, address = self.socket.accept()

            connection = Connection(clientSocket, self)
            connection.start()


    def executeProtocol(self, connection, message):       
        match message["message_name"]:
            case "AUTH":
                self.handle_AUTH(connection, message)
            case _:
                print("ERROR")

    def handle_AUTH(self, connection, message):
        username = message["username"]
        hashed_pword = message["hashed_password"]
        if (username in self.userList) and hashed_pword == (self.userList[username]):
            connection.authenticated = True
            connection.loggedInAs = username
            self.AUTH_OK(connection)
        else:
            self.AUTH_FAIL(connection)

    def AUTH_OK(self, connection):
        welcome_message = f'Welcome back, {connection.loggedInAs}!'

        connection.sendJson({
            "message_name": "AUTH_OK", 
            "data": {"welcome_message": welcome_message}
                })

    def AUTH_FAIL(self, connection):
        error_code = "INCORRECT USERNAME OR PASSWORD"
        connection.sendJson({
            "message_name": "AUTH_FAIL",
            "data": {"error_code": error_code}
        })


def main():
    server = Server("", 12000)
    server.listen()


if __name__ == "__main__":
    main()