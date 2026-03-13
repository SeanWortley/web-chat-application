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
        threading.Thread(target=self._connect_and_run, daemon=True).start()

    def _connect_and_run(self):
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
        self.command_queue.put(input_data)

    def process_commands(self):
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
        self.database = Database(self.loggedInAs)
        self.interface.database = self.database

    def unassign_db(self):
        self.database = None
        self.interface.database = None

    def initialise(self):
        pass

    def _on_udp_event(self, event, transfer_id, data=None):
        if event == 'progress':
            self.interface.update_progress(transfer_id, data)
        elif event == 'complete':
            self.interface.transfer_complete(transfer_id, data)
            self.udp_handler = None

    def accept_transfer(self, transfer_id):
        if transfer_id not in self.interface.pending_incoming:
            self.interface.display(f"No pending offer with ID {transfer_id}")
            return

        offer = self.interface.pending_incoming[transfer_id]
        del self.interface.pending_incoming[transfer_id]

        self.queue_user_input({
            "message_name": "MEDIA_RESPONSE",
            "data": {
                "chat_id": offer['sender'],
                "chat_type": offer['chat_type'],
                "status": "ACCEPT",
                "transfer_id": transfer_id,
                "filename": offer['filename']
            }
        })

    def reject_transfer(self, transfer_id):
        if transfer_id not in self.interface.pending_incoming:
            self.interface.display(f"No pending offer with ID {transfer_id}")
            return

        offer = self.interface.pending_incoming[transfer_id]
        del self.interface.pending_incoming[transfer_id]

        self.queue_user_input({
            "message_name": "MEDIA_RESPONSE",
            "data": {
                "chat_id": offer['sender'],
                "chat_type": offer['chat_type'],
                "status": "REJECT",
                "transfer_id": transfer_id
            }
        })


def main():
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
