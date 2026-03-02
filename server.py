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

    def listen(self):
        while True:
            clientSocket, adress = self.socket.accept()

            client = {"socket": clientSocket, "authenticated": False}
            Thread(target = self.handleClient, args = (client,)).start()

    def handleClient(self, client):
        while True:
            clientMessage = client["socket"].recv(1024).decode()
            self.executeProtocol(client, clientMessage)

    def executeProtocol(self, client, clientMessage):
        clientMessage = json.loads(clientMessage)
        
        match clientMessage["message_name"]:
            case "AUTH":
                self.auth(client, clientMessage)
            case _:
                print("ERROR")

    def auth(self, client, clientMessage):
        username = clientMessage["username"]
        hashed_pword = clientMessage["hashed_password"]
        if hashed_pword == self.clientList["username"]:
            client["authenticated"] == True
            print(f"Welcome back {username}!")
        else:
            print(f"Incorrect username or password!")



def main():
    server = Server.innit()
    server.listen()


if __name__ == main:
    main()