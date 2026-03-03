from socket import *
from connection import Connection
from protocol import Protocol
#Hello

class Client:
    def __init__(self, host, port):
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.connect((host, port))

        self.protocol = Protocol(self)
        self.connection = Connection(self.socket, self)
        self.connection.start()

        self.username = None
        self.authenticated = False

    def signIn(self):
        choice = input("Would you like to sign-in to an existing account? (Yes/No) \n If you don't have one, enter 'no' to create one.\n")
        if (choice.lower() == "yes") or (choice.lower() == "y"):
            self.protocol.AUTH(self.connection)
        else:
            self.protocol.CREATE_ACCOUNT(self.connection)


def main():
    client = Client("", 12000)
    client.signIn()

if __name__ == "__main__":
    main()