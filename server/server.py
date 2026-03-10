from ast import main
from re import T
from socket import *
from hashlib import sha256
from connection import Connection
from protocol import Protocol
from database import Database
import argparse
import os



class Server:    
    def __init__(self, host, port, verbose):
        self.verbose = verbose
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.protocol = Protocol(self)
        self.database = Database()
        self.socket.listen()
        #self.groups = {}  # stores groups: {group_name: [username1, username2]}
        self.connections = []  # track all active connections

    def listen(self):
        while True:
            clientSocket, address = self.socket.accept()
            connection = Connection(clientSocket, self)
            self.connections.append(connection)  # track active connection
            connection.start()

    def get_connection_by_username(self, username):
        for conn in self.connections:
            if conn.loggedInAs == username:
                return conn
        return None
    
    def log(self, message):
        if self.verbose:
            print(f"GENERAL: {message}")
    
    def log_incoming(self, message):
        if self.verbose:
            print(f"INCOMING: {message}")
        
    def log_outgoing(self, message):
        if self.verbose:
            print(f"OUTGOING: {message}")


def main():
    # Parse in arguements
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12000)
    parser.add_argument("--verbose", type=bool, default=True)
    args = parser.parse_args()
    print(args.host, args.port, args.verbose)

    server = Server(args.host, args.port, args.verbose)
    server.listen()


if __name__ == "__main__":
    main()