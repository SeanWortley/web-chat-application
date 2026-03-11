from socket import *
import time
from connection import Connection
from protocol import Protocol
from terminal import Terminal
from udp_handler import UDPHandler

class Client:
    def __init__(self, host, port, interface):
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.connect((host, port))

        self.username = None
        self.authenticated = False

        self.udp = UDPHandler(self.socket, self)
        self.udp.handler = None
        self.udp_port = 99999   # placeholder

        self.interface = interface
        self.interface.client = self          # <-- ADD THIS LINE
        self.interface.on_user_input = self.handle_user_input
        self.interface.start()                 # Now the thread has the reference

        self.protocol = Protocol(self)
        self.connection = Connection(self.socket, self)
        self.connection.start()

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
            case "MSG":  
                input["data"]["from"] = self.username
                input["data"]["msg_id"] = f"msg_{int(time.time())}"
                input["data"]["timestamp"] = time.time()
                self.protocol.MSG(self.connection, 
                            input["data"]["chat_id"],
                            input["data"]["chat_type"],
                            input["data"]["payload"])
            case _:
                pass

def main():
    interface = Terminal()
    client = Client("127.0.0.1", 12000, interface)

if __name__ == "__main__":
    main()
