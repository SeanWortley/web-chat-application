from socket import *
import argparse
import threading
import sys

from ..transport.connection import Connection
from ..protocol.protocol import Protocol
from ..storage.database import Database


class Server:
    def __init__(self, host, port, verbose):
        self.verbose = verbose
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.protocol = Protocol(self)
        self.database = Database()
        self.socket.listen()
        self.socket.settimeout(1.0)
        self.connections = []
        self.active_users = []
        self.running = True

    def listen(self):
        while self.running:
            try:
                clientSocket, address = self.socket.accept()
                clientSocket.settimeout(None)
                connection = Connection(clientSocket, self)
                self.connections.append(connection)
                connection.start()
            except (timeout, TimeoutError):
                continue
            except OSError:
                break

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

    def quit(self):
        print("Shutting down")
        self.running = False
        for connection in self.connections[:]:
            try:
                self.protocol.SHUTDOWN(connection)
            except Exception:
                pass
            connection.close()
        self.socket.close()

    def listen_for_quit(self):
        while self.running:
            try:
                text = input()
                if text == "/quit":
                    self.quit()
                    break
            except EOFError:
                break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12000)
    parser.add_argument("--verbose", type=bool, default=True)
    parser.add_argument("--clean", action="store_true", default=False)
    args = parser.parse_args()
    print(args.host, args.port, args.verbose)

    if args.clean: # If --clean is specified, clean the runtime files instead of starting the server :)
        from pathlib import Path
        runtime_db_dir = Path(__file__).resolve().parents[2] / "runtime" / "db"
        for db_file in runtime_db_dir.glob("*.db"):
            try:
                db_file.unlink()
            except OSError:
                pass
        return
    
    server = Server(args.host, args.port, args.verbose)

    quitting_thread = threading.Thread(target=server.listen_for_quit)
    quitting_thread.start()

    server.listen()
    sys.exit(0)


if __name__ == "__main__":
    main()
