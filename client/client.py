from socket import *
import time
import queue
import threading
from connection import TCPConnection, UDPConnection
from protocol import CSProtocol, P2PProtocol
from terminal import Terminal
from database import Database
import argparse
import sys
from gui import GUI
from terminal import Terminal


class Client:
    def __init__(self, host, port, interface):
        self.host = host
        self.port = port
        self.interface = interface
        self.interface.on_user_input = self.queue_user_input
        
        self.loggedInAs = None
        self.authenticated = False
        self.running = True
        
        # Command queue for thread-safe operation
        self.command_queue = queue.Queue()
        
        # Socket and protocol will be initialized in start()
        self.socket = None
        self.connection = None
        self.cs_protocol = None

        self.p2p_protocol = None
        self.udp_connection = None

        self.pending_transfers = {}
        
    def start(self):
        """Start the client connection in a background thread"""
        threading.Thread(target=self._connect_and_run, daemon=True).start()
        
    def _connect_and_run(self):
        """Connect to server and run client loop"""
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
            
            # Start command processor
            self.process_commands()
            
        except Exception as e:
            print(f"Connection error: {e}")
    
    def queue_user_input(self, input_data):
        """Queue user input for safe processing"""
        self.command_queue.put(input_data)

    def process_commands(self):
        """Process queued commands in the connection thread"""
        while self.running:
            try:
                # Wait for a command with timeout
                cmd = self.command_queue.get(timeout=0.1)
                self._handle_user_input(cmd)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error processing command: {e}")
                break

    def _handle_user_input(self, input_data):
        """Actually handle the user input"""
        # Make sure protocol is ready
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
                #handler = self.get_udp_handler() 
                #port = handler.get_port() if handler else None

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

    """
    def get_udp_handler(self):
        
        if not self.udp_handler and self.authenticated:
            # Just create - all logic is inside udp_handler.py
            from udp_handler import UDPHandler
            self.udp_handler = UDPHandler(self, callback=self._on_udp_event)
            self.udp_handler.start()  # Start listening
        return self.udp_handler
    """
    def _on_udp_event(self, event, transfer_id, data=None):
        """Handle UDP events - just forward to UI"""
        if event == 'progress':
            self.interface.update_progress(transfer_id, data)
        elif event == 'complete':
            self.interface.transfer_complete(transfer_id, data)
            self.udp_handler = None  # Clear reference
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=12000)    
    parser.add_argument("--terminal", action="store_true", default=False)
    args = parser.parse_args()
    print(args)

    if args.terminal:
        interface = Terminal()
    else:
        interface = GUI()
    client = Client(args.host, args.port, interface)
    # Start client in background thread
    client.start()
    # Run GUI in main thread
    interface.start()

if __name__ == "__main__":
    main()