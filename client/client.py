from socket import *
import time
import queue
import threading
from connection import Connection
from protocol import Protocol
from gui import GUI
from terminal import Terminal

class Client:
    def __init__(self, host, port, interface):
        self.host = host
        self.port = port
        self.interface = interface
        self.interface.on_user_input = self.queue_user_input
        
        self.username = None
        self.authenticated = False
        self.running = True
        
        # Command queue for thread-safe operation
        self.command_queue = queue.Queue()
        
        # Socket and protocol will be initialized in start()
        self.socket = None
        self.connection = None
        self.protocol = None
        
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
                input_data["data"]["from"] = self.username
                input_data["data"]["msg_id"] = f"msg_{int(time.time())}"
                input_data["data"]["timestamp"] = time.time()
                self.protocol.MSG(self.connection, 
                                input_data["data"]["chat_id"],
                                input_data["data"]["chat_type"],
                                input_data["data"]["payload"])
            case _:
                print(f"Unknown command: {input_data}")

    def initialise(self):
        pass

def main():
    interface = GUI()
    #interface = Terminal()
    client = Client("127.0.0.1", 12000, interface)
    
    # Start client in background thread
    client.start()
    
    # Run GUI in main thread
    interface.start()

if __name__ == "__main__":
    main()