from socket import *
import time
import queue
import threading
import argparse
import sys
from ..transport import TCPConnection, UDPConnection
from ..protocol import CSProtocol, P2PProtocol
from ..storage import Database
from ..ui import GUI, Terminal


class Client:
    def __init__(self, host, port, interface):
        """
        Initializes a client instance with server connection and UI interface.

        Args:
            host (str): Server hostname or IP.
            port (int): Server port number.
            interface (Interface): User interface object for input/output.

        Attributes:
            loggedInAs (str | None): Username of the logged-in user.
            authenticated (bool): Whether the client has successfully authenticated.
            running (bool): Whether the client is actively running.
            command_queue (queue.Queue): Stores commands from user input.
            socket (socket | None): TCP socket to the server.
            connection (Connection | None): Wrapper for server connection.
            cs_protocol (Protocol | None): Protocol handler for client-server communication.
            p2p_protocol (Protocol | None): Protocol handler for peer-to-peer communication.
            udp_connection (socket | None): Optional UDP socket for direct transfers.
            pending_transfers (dict): Tracks ongoing file or media transfers.
        """
        self.host = host
        self.port = port
        self.interface = interface
        self.interface.on_user_input = self.queue_user_input

        self.loggedInAs = None
        self.authenticated = False
        self.running = True

        self.command_queue = queue.Queue()

        self.socket = None
        self.connection = None
        self.cs_protocol = None

        self.p2p_protocol = None
        self.udp_connection = None

        self.pending_transfers = {}

    def start(self):
        """
        Starts the client by connecting to the server in a background thread.
        """
        threading.Thread(target=self._connect_and_run, daemon=True).start()

    def _connect_and_run(self):
        """
        Establishes TCP and P2P connections, initializes protocols, and
        starts processing user commands.
        """
        try:
            self.socket = socket(AF_INET, SOCK_STREAM)
            self.socket.connect((self.host, self.port))

            self.cs_protocol = CSProtocol(self)
            self.connection = TCPConnection(self.socket, self)
            self.connection.start()

            self.p2p_protocol = P2PProtocol(self, None)
            self.udp_connection = UDPConnection(self.p2p_protocol)

            self.p2p_protocol.udp = self.udp_connection
            self.udp_port = self.udp_connection.start()

            self.process_commands()

        except Exception as e:
            print(f"Connection error: {e}")

    def queue_user_input(self, input_data):
        """
        Adds a user command to the command queue for processing.

        Args:
            input_data (dict): Command or message from the user interface.
        """
        self.command_queue.put(input_data)

    def process_commands(self):
        """
        Continuously processes commands from the user input queue until
        the client stops running.
        """
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=0.1)
                self._handle_user_input(cmd)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing command: {e}")
                break

    def _handle_user_input(self, input_data):
        """
        Dispatches a user input command to the appropriate client-server
        or P2P protocol method.

        Args:
            input_data (dict): Contains message_name and data for processing.
        """
        if not hasattr(self, 'cs_protocol') or self.cs_protocol is None:
            print("Protocol not ready, requeueing...")
            self.command_queue.put(input_data)
            time.sleep(0.1)
            return

        match input_data["message_name"]:
            case "AUTH":
                self.cs_protocol.AUTH(self.connection,
                                      input_data["data"]["username"],
                                      input_data["data"]["hashed_password"])
            case "CREATE_ACCOUNT":
                self.cs_protocol.CREATE_ACCOUNT(self.connection,
                                                input_data["data"]["username"],
                                                input_data["data"]["hashed_password"])
            case "LOGOUT":
                self.cs_protocol.LOGOUT(self.connection)
            case "CREATE_GROUP":
                self.cs_protocol.CREATE_GROUP(self.connection,
                                              input_data["data"]["group_name"])
            case "JOIN_GROUP":
                self.cs_protocol.JOIN_GROUP(self.connection,
                                            input_data["data"]["group_name"])
            case "GROUP_LIST":
                self.cs_protocol.GROUP_LIST(self.connection)
            case "MSG":
                input_data["data"]["from"] = self.loggedInAs
                input_data["data"]["msg_id"] = f"msg_{int(time.time())}"
                input_data["data"]["timestamp"] = time.time()
                self.cs_protocol.MSG(self.connection,
                                     input_data["data"]["chat_id"],
                                     input_data["data"]["chat_type"],
                                     input_data["data"]["payload"])
            case "MEDIA_OFFER":
                input_data["data"]["from"] = self.loggedInAs
                input_data["data"]["sender_port"] = self.udp_port
                self.cs_protocol.MEDIA_OFFER(self.connection,
                                             input_data["data"]["chat_id"],
                                             input_data["data"]["transfer_id"],
                                             input_data["data"]["filepath"],
                                             input_data["data"]["chat_type"],
                                             input_data["data"]["sender_port"])

            case "MEDIA_RESPONSE":
                input_data["data"]["from"] = self.loggedInAs
                input_data["data"]["receiver_port"] = self.udp_port
                filename = input_data["data"].get("filename")
                if filename and input_data["data"]["status"].upper() == "ACCEPT":
                    self.p2p_protocol.recv_filenames[input_data["data"]["transfer_id"]] = filename
                self.cs_protocol.MEDIA_RESPONSE(self.connection,
                                                input_data["data"]["chat_id"],
                                                input_data["data"]["chat_type"],
                                                input_data["data"]["status"],
                                                input_data["data"]["transfer_id"],
                                                input_data["data"]["receiver_port"])
            case "close_connection":
                self.connection.close()
            case "quit_program":
                sys.exit(0)
            case "shutdown":
                self.interface.process_shutdown()
            case "REQUEST_UNSENT_MESSAGES":
                self.cs_protocol.REQUEST_UNSENT_MESSAGES(self.connection)
            case _:
                print(f"Unknown command: {input_data}")

    def assign_db(self):
        """
        Assigns a database instance to the client and the interface.
        """
        self.database = Database(self.loggedInAs)
        self.interface.database = self.database

    def unassign_db(self):
        """
        Removes the database assignment from the client and the interface.
        """
        self.database = None
        self.interface.database = None


def main():
    """
    Entry point for running the client application.

    Parses command-line arguments, optionally cleans runtime files,
    initializes the interface (GUI or terminal), and starts the client.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12000)
    parser.add_argument("--terminal", action="store_true", default=False)
    parser.add_argument("--clean", action="store_true", default=False)
    args = parser.parse_args()
    print(args)

    if args.clean:
        from pathlib import Path
        runtime_db_dir = Path(__file__).resolve().parents[2] / "runtime" / "db"
        for db_file in runtime_db_dir.glob("*.db"):
            try:
                db_file.unlink()
            except OSError:
                pass
        return

    if args.terminal:
        interface = Terminal()
    else:
        interface = GUI()
    client = Client(args.host, args.port, interface)
    client.start()
    interface.start()


if __name__ == "__main__":
    main()
