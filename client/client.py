from socket import *
import time
from connection import Connection
from protocol import Protocol
from terminal import Terminal
from database import Database
import sys

class Client:
    def __init__(self, host, port, interface):
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.connect((host, port))

        self.loggedInAs = None
        self.authenticated = False

        self.interface = interface
        self.interface.on_user_input = self.handle_user_input
        self.interface.start()

        self.protocol = Protocol(self)
        self.connection = Connection(self.socket, self)
        self.connection.start()

    def initialise(self):
        pass

    def handle_user_input(self, input):
        match input["message_name"]:
            case "AUTH":
                self.protocol.AUTH(self.connection, input["data"]["username"], input["data"]["hashed_password"])
            case "CREATE_ACCOUNT":
                self.protocol.CREATE_ACCOUNT(self.connection, input["data"]["username"], input["data"]["hashed_password"])
            case "LOGOUT":
                self.protocol.LOGOUT(self.connection)
            case "CREATE_GROUP":
                self.protocol.CREATE_GROUP(self.connection, input["data"]["group_name"])
            case "JOIN_GROUP":
                self.protocol.JOIN_GROUP(self.connection, input["data"]["group_name"])
            case "GROUP_LIST":
                self.protocol.GROUP_LIST(self.connection)
            case "MSG":  
                input["data"]["from"] = self.loggedInAs
                input["data"]["msg_id"] = f"msg_{int(time.time())}"
                input["data"]["timestamp"] = time.time()
                self.protocol.MSG(self.connection, 
                            input["data"]["chat_id"],
                            input["data"]["chat_type"],
                            input["data"]["payload"])
            case "close_connection":
                self.connection.close()
            case "quit_program":
                self.quit_program()
            case _:
                pass
    def assign_db(self):
        self.database = Database(self.loggedInAs)
        self.interface.database = self.database

    def unassign_db(self):
        self.database = None
        self.interface.database = None

    def quit_program(self):
        sys.exit(0)

def main():
    interface = Terminal()
    client = Client("127.0.0.1", 12000, interface)

if __name__ == "__main__":
    main()
