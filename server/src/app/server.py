from socket import *
import argparse
import threading
import sys

from ..transport.connection import Connection
from ..protocol.protocol import Protocol
from ..storage.database import Database


class Server:
    def __init__(self, host, port, verbose):
        """
    Initializes the server instance and prepares all required components.

    This constructor creates and configures the server socket, initializes
    the protocol handler and database, and sets up internal structures used
    to manage client connections and active users.

    Args:
        host (str): The hostname or IP address the server will bind to.
        port (int): The port number the server will listen on.
        verbose (bool): Enables verbose logging for debugging and
            connection monitoring if set to True.

    Attributes:
        verbose (bool): Controls whether logging output is printed.
        socket (socket): The TCP server socket used to accept connections.
        protocol (Protocol): The protocol handler responsible for
            processing client requests.
        database (Database): Database interface used for storing and
            retrieving application data.
        connections (list): List of active client connection objects.
        active_users (list): List of users currently connected to the server.
        running (bool): Indicates whether the server main loop is active.
    """
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
        """
        Continuously listens for incoming client connections and starts a new
        connection thread for each accepted client.

        The method runs while the server is active (`self.running`). When a client
        connects, the socket is accepted, wrapped in a `Connection` object, stored
        in the server's connection list, and started in its own thread.

        The method safely handles timeout-related exceptions and stops listening
        if the server socket is closed.

        Args:
            self (Server): The server instance managing the listening socket and
                active connections.

        Raises:
            OSError: Raised when the server socket is closed, causing the listening
                loop to terminate.
        """
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

    def log(self, message):
        """
        Logs a general message if verbose mode is enabled.

        Args:
            message (str): The message to display in the console.
        """
        if self.verbose:
            print(f"GENERAL: {message}")

    def log_incoming(self, message):
        """
        Logs a message received from a client if verbose mode is enabled.

        Args:
            message (str): The incoming message to display.
        """
        if self.verbose:
            print(f"INCOMING: {message}")

    def log_outgoing(self, message):
        """
        Logs a message sent to a client if verbose mode is enabled.

        Args:
            message (str): The outgoing message to display.
        """
        if self.verbose:
            print(f"OUTGOING: {message}")

    def quit(self):
        """
        Shuts down the server and closes all active connections.

        This method stops the main server loop, attempts to notify each
        connected client of the shutdown via the protocol handler, closes
        all connections, and finally closes the server socket.
        """
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
        """
        Listens for console input to trigger a server shutdown.

        While the server is running, this method waits for user input.
        If the command '/quit' is entered, the server shutdown process
        is initiated.

        Raises:
            EOFError: Raised if the input stream closes unexpectedly.
        """
        while self.running:
            try:
                text = input()
                if text == "/quit":
                    self.quit()
                    break
            except EOFError:
                break


def main():
    """
    Entry point for starting or cleaning the server runtime environment.

    This function parses command-line arguments for host configuration,
    port selection, verbosity, and cleanup mode. If `--clean` is specified,
    it removes all `.db` files from the runtime database directory and exits.
    Otherwise, it initializes and runs the server instance.

    Command-line Arguments:
        --host (str): The hostname or IP address to bind the server to. Default is '127.0.0.1'.
        --port (int): The port number to listen on. Default is 12000.
        --verbose (bool): Enables verbose logging if True. Default is True.
        --clean (flag): If provided, cleans runtime `.db` files and exits without starting the server.

    Workflow:
        1. Parse command-line arguments.
        2. If `--clean` is passed, delete runtime database files and exit.
        3. Otherwise, start a `Server` instance and listen for incoming connections.
        4. Start a background thread to listen for a `/quit` command.

    Raises:
        OSError: If there is an issue deleting runtime files during cleanup.
    """
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
