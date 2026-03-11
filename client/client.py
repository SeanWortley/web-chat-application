from socket import *
import time
import queue
import threading
from connection import Connection
from protocol import Protocol
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
        self.protocol = None

        self.udp_port = 99999 
        
    def start(self):
        """Start the client connection in a background thread"""
        threading.Thread(target=self._connect_and_run, daemon=True).start()
        
    def _connect_and_run(self):
        """Connect to server and run client loop"""
        try:
            self.socket = socket(AF_INET, SOCK_STREAM)
            self.socket.connect((self.host, self.port))

            self.protocol = Protocol(self)
            self.connection = Connection(self.socket, self)
            self.connection.start()
            
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
        if not hasattr(self, 'protocol') or self.protocol is None:
            print("Protocol not ready, requeueing...")
            self.command_queue.put(input_data)
            time.sleep(0.1)
            return
            
        match input_data["message_name"]:
            case "AUTH":
                self.protocol.AUTH(self.connection, 
                                  input_data["data"]["username"], 
                                  input_data["data"]["hashed_password"])
            case "CREATE_ACCOUNT":
                self.protocol.CREATE_ACCOUNT(self.connection, 
                                           input_data["data"]["username"], 
                                           input_data["data"]["hashed_password"])
            case "LOGOUT":
                self.protocol.LOGOUT(self.connection)
            case "CREATE_GROUP":
                self.protocol.CREATE_GROUP(self.connection, 
                                          input_data["data"]["group_name"])
            case "JOIN_GROUP":
                self.protocol.JOIN_GROUP(self.connection, 
                                        input_data["data"]["group_name"])
            case "GROUP_LIST":
                self.protocol.GROUP_LIST(self.connection)
            case "MSG":  
                input_data["data"]["from"] = self.loggedInAs
                input_data["data"]["msg_id"] = f"msg_{int(time.time())}"
                input_data["data"]["timestamp"] = time.time()
                self.protocol.MSG(self.connection, 
                                input_data["data"]["chat_id"],
                                input_data["data"]["chat_type"],
                                input_data["data"]["payload"])
            case "MEDIA_OFFER":
                #handler = self.get_udp_handler() 
                #port = handler.get_port() if handler else None

                input["data"]["from"] = self.username
                input["data"]["transfer_id"] = f"transferID_{int(time.time())}"
                input["data"]["sender_port"] = 88888
                self.protocol.media_offer(self.connection,
                            input["data"]["chat_id"],
                            input["data"]["filepath"],
                            input["data"]["chat_type"],
                            input["data"]["sender_port"])
                
            case "MEDIA_RESPONSE":
                #handler = self.get_udp_handler() 
                #port = handler.get_port() if handler else None

                input["data"]["from"] = self.username
                input["data"]["receiver_port"] = 99999
                self.protocol.media_response(self.connection,
                            input["data"]["chat_id"],
                            input["data"]["chat_type"],
                            input["data"]["status"],
                            input["data"]["transfer_id"],
                            input["data"]["receiver_port"])
            case "close_connection":
                self.connection.close()
            case "quit_program":
                sys.exit(0)
            case "REQUEST_UNSENT_MESSAGES":
                self.protocol.REQUEST_UNSENT_MESSAGES(self.connection)
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

    def get_udp_handler(self):
        """Get or create UDP handler"""
        if not self.udp_handler and self.authenticated:
            # Just create - all logic is inside udp_handler.py
            from udp_handler import UDPHandler
            self.udp_handler = UDPHandler(self, callback=self._on_udp_event)
            self.udp_handler.start()  # Start listening
        return self.udp_handler
    
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