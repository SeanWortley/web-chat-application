from ast import main
from socket import *
from hashlib import sha256
from connection import Connection
from protocol import Protocol
from database import Database


class Server:
    userList = {"username": sha256("password".encode()).hexdigest(), "admin": sha256("admin".encode()).hexdigest()}

    def __init__(self, host, port):
        self.running = True
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.database = Database()
        self.protocol = Protocol(self)
        self.socket.listen()

    def listen(self):
        while True:
            clientSocket, address = self.socket.accept()

            connection = Connection(clientSocket, self)
            connection.start()

    def input_loop(self):
        while self.running:
            text = input("> ")

            if text in self.commands:
                command = self.commands.get(text)
                self.wait_event.clear()
                command()
                self.wait_event.wait()

            else: 
                print("Invalid command. Try /help")

def main():
    server = Server("", 12000)
    server.listen()
    server.input_loop()


if __name__ == "__main__":
    main()