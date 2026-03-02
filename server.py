from ast import main
from socket import *
from threading import Thread
import json
import time


class Server:
    userList = {"username": hash("password")}

    def __init__(self, host, port):
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.bind((host, port))
        self.socket.listen()

    def listen(self):
        while True:
            clientSocket, adress = self.socket.accept()

            client = {"socket": clientSocket, "authenticated": False}
            Thread(target = self.handleClient, args = (client,)).start()

    def handleClient(self, client):
        while True:
            clientMessage = json.loads(client["socket"].recv(1024).decode())
            self.executeProtocol(client, clientMessage)

    def executeProtocol(self, client, clientMessage):       
        match clientMessage["message_name"]:
            case "AUTH":
                self.AUTH(client, clientMessage)
            case _:
                print("ERROR")

    def AUTH(self, client, clientMessage):
        username = clientMessage["username"]
        hashed_pword = clientMessage["hashed_password"]
        if (username in self.userList) and hashed_pword == (self.userList[username]):
            self.AUTH_OK(client)
        else:
            self.AUTH_FAIL(client)

    def AUTH_OK(self, client):
        client["authenticated"] = True
        welcome_message = f'Welcome back, {client["username"]}!'
        serverMessage = json.dumps({
            "message_name": "AUTH_OK", 
            "data": {"welcome_message": welcome_message}
                })
        client["socket"].send(serverMessage.encode())

    def AUTH_FAIL(self, client):
        error_code = "INCORRECT USERNAME OR PASSWORD"
        serverMessage = json.dumps({
            "message_name": "AUTH_FAIL",
            "data": {"error_code": error_code}
        })
        client["socket"].send(serverMessage.encode())


def main():
    server = Server("", 12000)
    server.listen()


if __name__ == "__main__":
    main()