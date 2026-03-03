from socket import *
from hashlib import sha256
import json

class Client:
    authenticated = False

    def __init__(self, host, port):
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.connect((host, port))

    def run(self):
        self.AUTH()

    def executeProtocol(self, serverMessage):
        match serverMessage["message_name"]:
            case "AUTH_OK":
                self.handle_AUTH_OK(serverMessage)
            case "AUTH_FAIL":
                self.handle_AUTH_FAIL(serverMessage)
            case _:
                print("ERROR, INVALID INCOMING MESSAGE")

    def AUTH(self):
        self.username = input("Enter your username: ")
        hashed_pword = (sha256(input("Enter your password: ").encode())).hexdigest()
        
        clientMessage = json.dumps({"message_name": "AUTH", "username": self.username, "hashed_password": hashed_pword})
        self.socket.send(clientMessage.encode())

        serverMessage = json.loads(self.socket.recv(1024).decode())
        self.executeProtocol(serverMessage)

    def handle_AUTH_OK(self, serverMessage):
        self.authenticated = True
        print(serverMessage["data"]["welcome_message"])

    def handle_AUTH_FAIL(self, serverMessage):
        print(f"Failed to authenticate: {serverMessage["data"]["error_code"]}")


def main():
    client = Client("", 12000)
    client.run()

if __name__ == "__main__":
    main()