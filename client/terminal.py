from threading import Thread, Event
from hashlib import sha256
from tokenize import group
import queue
import os
import time
import sys
import uuid
from pathlib import Path

class Terminal:

    def __init__(self):
        self.commands = {
            "/help": self.displayHelp,
            "/login": self.login,
            "/register": self.register,
            "/logout": self.logout,
            "/current": self.print_current
        }
        self.on_user_input = None
        self.wait_event = Event()
        self.running = True
        self.logged_in = False
        self.chatting_mode = False

        self.pending_incoming = {}  # for when they don't reply right away the must keep the offer somewhere
        self.pending_outgoing = {}  # for them to later know the details when the receiver eventually replies

        self.unread_messages = {}
        self.current_chat = None # Is either 'from' or 'group_name' depending on chat type

    def start(self):
        print("Welcome to the terminal interface for our chat application!")
        print("To get started, type '/login', '/register', or '/help' for a list of commands.")
        self.show_logged_out_menu()
        Thread(target=self.input_loop).start()

    def input_loop(self):
        while self.running:
            text = input("> ").strip()

            if self.running: # This is to stop the "Invalid command" prompt after pressing enter to exit :)

                if text == "1": #Private chat
                    self.start_private_chat()
                    self.current_chat = None

                elif text == "2": #Group chat
                    self.start_group_chat()
                    self.current_chat = None

                elif text == "3":
                    self.wait_event.clear()
                    self.view_groups()
                    self.wait_event.wait()
                elif text == "4":
                    self.wait_event.clear()
                    self.create_group()
                    self.wait_event.wait()
                elif text == "5":
                    self.wait_event.clear()
                    self.join_group()
                    self.wait_event.wait()
                
                elif text == "/quit":
                    self.quit()
                    break

                elif text in self.commands:
                    command = self.commands.get(text)
                    self.wait_event.clear()
                    command()
                    self.wait_event.wait()

                elif text.startswith("/accept"):
                    parts = text.split()
                    if len(parts) == 2:
                        transfer_id = int(parts[1])
                        self.accept_transfer(transfer_id)
                    else:
                        print("Usage: /accept <transfer_id>")

                elif text.startswith("/reject"):
                    parts = text.split()
                    if len(parts) == 2:
                        transfer_id = int(parts[1])
                        self.reject_transfer(transfer_id)
                    else:
                        print("Usage: /reject <transfer_id>")

                else:
                    print("Invalid command. Try /help")

    def process_unsent_batch(self, groups):
        for chat_id, messages in groups.items():
            num = len(messages)
            print(f"\n[{num}] UNREAD MESSAGE(S) FROM {chat_id.upper()}")
            print("> ", end="")

            for message in messages:
                standard_form = {
                    "data": {
                        "from": message["sender"],
                        "chat_id": chat_id,
                        "chat_type": message["chat_type"],
                        "payload": message["content"],
                        "timestamp": message["timestamp"]
                    }
                }
                self.queue_msg(standard_form)

    def process_msg(self, message, channel):
        if channel != self.current_chat:
            self.queue_msg(message)
            self.notify_msg(message)
   
        else:
            # It's a plain text message
            self.print_msg(message)


    def process_unread_in_current_chat(self):
        if self.current_chat not in self.unread_messages:
            return
        
        q = self.unread_messages[self.current_chat]
        while not q.empty():
            message = q.get()
            self.print_msg(message, True)
        del self.unread_messages[self.current_chat]


    def queue_msg(self, message):
        data = message.get("data")
        from_user = data.get("from")
        chat_type = data.get("chat_type")
        chat_id = data.get("chat_id")

        # This just makes it match how we keep track of current_chat :)
        if chat_type == "private":
            key = from_user
        else:
            key = chat_id

        if key in self.unread_messages:
            self.unread_messages[key].put(message)

        else:
            unread_queue = queue.Queue()
            unread_queue.put(message)
            self.unread_messages[key] = unread_queue

        
    def notify_msg(self, message):
        data = message.get("data")
        from_user = data.get("from")
        chat_type = data.get("chat_type")
        chat_id = data.get("chat_id")

        if chat_type == "private":
            notification_message = f'\n[NEW PRIVATE MESSAGE FROM {from_user.upper()}]'
        else:
            notification_message = f'\n[NEW MESSAGE IN |{chat_id.upper()}| FROM {from_user.upper()}]'

        if self.chatting_mode:
            notification_message = f'{notification_message}\n>> '
        else:
            notification_message = f'{notification_message}\n> '


        print(notification_message, end="")

    
    def print_msg(self, message, is_unread=False):
        data = message.get("data")
        from_user = data.get("from")
        if is_unread:
            print(f'{from_user}: {data.get("payload")}')
        else:
            print(f'\n{from_user}: {data.get("payload")}\n>> ', end="")

    def load_private_logs(self, chat_id):
        logs = self.database.get_chat_history(chat_id, "private")
        for message in logs:
            from_user = message.get("from_user")
            msg_text = message.get("msg_text")
            sender = ">> " if (from_user == self.loggedInAs) else f"{from_user}: "
            print(sender + msg_text)
        print("-------------------------------------")
        
    def load_group_logs(self, chat_id):
        logs = self.database.get_chat_history(chat_id, "group")
        for message in logs:
            from_user = message.get("from_user")
            msg_text = message.get("msg_text")
            sender = ">> " if (from_user == self.loggedInAs) else f"{from_user}: "
            print(sender + msg_text)
        print("-------------------------------------")

    def start_private_chat(self):
        recipient = input("Who would you like to chat with?\n> ")
        self.current_chat = recipient
        self.chatting_mode = True
                
        self.clear()
        print(f"========= Entered private chat room with {recipient} =========")
        self.load_private_logs(recipient)
        print("Commands: /mdt <filepath> - send file")
        print("          /accept <transfer_id> - accept incoming file")
        print("          /reject <transfer_id> - reject incoming file")
        print("          /exit - leave")
        self.process_unread_in_current_chat()
        
        text = input(">> ")
        while text != "/exit" and self.running:
            if text.startswith("/mdt"):
                parts = text.split(maxsplit=1)
                if len(parts) == 1:
                    filepath = input("Enter filepath:\n> ").strip('')
                else:
                    filepath = parts[1].strip('')
                self.send_media_offer(recipient, filepath, chat_type="private")
            
            elif text.startswith("/accept"):
                parts = text.split()
                if len(parts) == 2:
                    transfer_id = int(parts[1])
                    self.accept_transfer(transfer_id)
                else:
                    print("Usage: /accept <transfer_id>")
            
            elif text.startswith("/reject"):
                parts = text.split()
                if len(parts) == 2:
                    transfer_id = int(parts[1])
                    self.reject_transfer(transfer_id)
                else:
                    print("Usage: /reject <transfer_id>")
            
            else:
                self.on_user_input({
                    "message_name": "MSG",
                    "data": {
                        "chat_id": recipient,
                        "chat_type": "private",
                        "payload": text
                    }
                })
            text = input(">> ")

        self.chatting_mode = False
        if self.running:
            self.show_logged_in_menu()

    def accept_transfer(self, transfer_id):
        if transfer_id not in self.pending_incoming:
            print(f"No pending offer with ID {transfer_id}")
            return
        
        offer = self.pending_incoming[transfer_id]

        # Send MEDIA_RESPONSE with status ACCEPT
        self.on_user_input({
            "message_name": "MEDIA_RESPONSE",
            "data": {
                "chat_id": offer['sender'],
                "chat_type": offer['chat_type'],
                "status": "ACCEPT",
                "transfer_id": transfer_id,
                "filename": offer['filename']
            }
        })
        
        # Remove from pending
        del self.pending_incoming[transfer_id]
        print(f" Accepted transfer {transfer_id}")


    def reject_transfer(self, transfer_id):
        if transfer_id not in self.pending_incoming:
            print(f"No pending offer with ID {transfer_id}")
            return
        
        offer = self.pending_incoming[transfer_id]
        
        self.on_user_input({
            "message_name": "MEDIA_RESPONSE",
            "data": {
                "chat_id": offer['sender'],
                "chat_type": offer['chat_type'],
                "status": "REJECT",
                "transfer_id": transfer_id
            }
        })
        
        del self.pending_incoming[transfer_id]
        print(f" Rejected transfer {transfer_id}") 

    def start_group_chat(self):
        group = input("Which chat room would you like to enter?\n> ")
        self.current_chat = group

        self.chatting_mode = True
        self.clear()
        print(f"Entered {group} chat room")
        self.load_group_logs(group)
        print("Commands: /mdt <filepath> - send file")
        print("          /accept <transfer_id> - accept incoming file")
        print("          /reject <transfer_id> - reject incoming file")
        print("          /exit - leave")
        self.process_unread_in_current_chat()
        text = input(">> ")
        while text != "/exit" and self.running:

            if text.startswith("/mdt"):
                parts = text.split(maxsplit=1)
                if len(parts) == 1:
                    filepath = input("Enter filepath:\n> ").strip('')
                else:
                    filepath = parts[1].strip('')
                    self.send_media_offer(group, filepath, chat_type="group")
            
            elif text.startswith("/accept"):
                parts = text.split()
                if len(parts) == 2:
                    transfer_id = int(parts[1])
                    self.accept_transfer(transfer_id)
                else:
                    print("Usage: /accept <transfer_id>")
            
            elif text.startswith("/reject"):
                parts = text.split()
                if len(parts) == 2:
                    transfer_id = int(parts[1])
                    self.reject_transfer(transfer_id)
                else:
                    print("Usage: /reject <transfer_id>")
            
            else:
                self.on_user_input({
                    "message_name": "MSG",
                    "data": {
                        "chat_id": group,
                        "chat_type": "group",
                        "payload": text
                    }
                })
            text = input(">> ")
        self.chatting_mode = False
        if self.running:
            self.show_logged_in_menu()
    
    def resume(self):
        self.wait_event.set()
    
    def displayHelp(self):
        print("=== MAIN MENU ===")
        print("/login")
        print("/register")
        print("/logout")
        print("/quit")
        print("=== CHAT MENU ===")
        print("1. Enter Private Chat")
        print("2. Enter Group Chat")
        print("3. View Groups")
        print("4. Create Group")
        print("5. Join Group")
        self.resume()

    def show_logged_out_menu(self):
        self.clear()
        print("=== MAIN MENU ===")
        print("/login")
        print("/register")
        print("/logout")
        print("/quit")

    def show_logged_in_menu(self):
        self.clear()
        print("=== CHAT MENU ===")
        print("1. Enter Private Chat")
        print("2. Enter Group Chat")
        print("3. View Groups")
        print("4. Create Group")
        print("5. Join Group")

    def login(self):
        username = input("Enter your username:\n> ")
        hashed_pword = (sha256(input("Enter your password:\n> ").encode())).hexdigest()
        
        self.on_user_input({
            "message_name": "AUTH",
            "data": {
                "username": username,
                "hashed_password": hashed_pword
            }
        })

    def register(self):
        username = input("Enter your desired username:\n> ")
        hashed_pword = (sha256(input("Enter your desired password:\n> ").encode())).hexdigest()

        self.on_user_input({
            "message_name": "CREATE_ACCOUNT",
            "data": {
                "username": username,
                "hashed_password": hashed_pword
            }
        })
        
    def logout(self):
        if self.logged_in:
            self.on_user_input({
                "message_name": "LOGOUT"
            })
        else:
            print("You are not logged in.")
            self.resume()

    def quit(self):
        self.running = False
        self.logout()
        self.on_user_input({
            "message_name": "close_connection"
        })
        self.on_user_input({
            "message_name": "quit_program"
        })
        
        sys.exit()

    def create_group(self):
        group_name = input("Enter your desired group name:\n> ")
        
        # Pass message to client.py
        self.on_user_input({
            "message_name": "CREATE_GROUP",
            "data": {
                "group_name": group_name
            }
        })
    
    def join_group(self):
        group_name = input("Enter the name of the group you'd like to join:\n> ")
        
        # Pass message to client.py
        self.on_user_input({
            "message_name": "JOIN_GROUP",
            "data": {
                "group_name": group_name
            }
        })

    def view_groups(self):
        self.on_user_input({
            "message_name": "GROUP_LIST"
        })

    def leave_group(self):
        group_name = input("Enter the name of the group you'd like to leave:\n> ")

        self.on_user_input({
            "message_name": "LEAVE_GROUP",
            "data": {
                "group_name": group_name
            }
        })

    def display(self, text): # Will have to be adapted once GUI is added.
        print(text)

    def private_message(self):
        recipient = input("Enter recipient username:\n> ")
        message = input("Enter your message:\n> ")
    
        self.send_message(recipient, message)

    def send_media_offer(self, chat_id, filepath, chat_type):

        filepath = filepath.strip().strip('"\'') 
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return
        transfer_id = uuid.uuid4().int & 0xFFFFFFFF
        self.pending_outgoing[transfer_id] = {
            'recipient': chat_id,
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'filesize': os.path.getsize(filepath),
            'chat_type': chat_type,
            'status': 'pending'
        }
        self.on_user_input({
            "message_name": "MEDIA_OFFER",
            "data": {
                    "chat_id": chat_id,
                    "transfer_id": transfer_id,
                    "filepath": filepath,
                    "chat_type": chat_type,
            }  
        })
    
    def handle_incoming_response(self, message):
        """
        Called when a MEDIA_RESPONSE arrives from the server.
        Handles both private and group transfers by accumulating responses.
        """
        data = message.get("data", {})
        transfer_id = data.get("transfer_id")
        status = data.get("status")
        receiver_port = data.get("receiver_port")
        receiver_ip = data.get("receiver_ip")   # added by server
        responder = data.get("from")

        if transfer_id not in self.pending_outgoing:
            print(f" Received response for unknown outgoing transfer {transfer_id}")
            return

        offer = self.pending_outgoing[transfer_id]

        # Initialize lists if not present (for group transfers)
        if 'accepted' not in offer:
            offer['accepted'] = []
        if 'rejected' not in offer:
            offer['rejected'] = []

        if status == "ACCEPT":
            print(f" {responder} accepted the file transfer!")
            # Store acceptor's connection details for later UDP transfer
            offer['accepted'].append({
                'user': responder,
                'ip': receiver_ip,
                'port': receiver_port
            })
            # For private transfers, you could immediately start UDP here
            # if len(offer['accepted']) == 1 and offer['chat_type'] == 'private':
            #     self.initiate_udp_to(offer['accepted'][0])
        elif status == "REJECT":
            print(f"{responder} rejected the file transfer")
            offer['rejected'].append(responder)
        else:
            print(f"Unknown response status: {status}")


    def handle_incoming_offer(self, message):
        data = message.get("data", {})
        transfer_id = data.get("transfer_id")
        if not transfer_id:
            return
        
        # Store the offer
        self.pending_incoming[transfer_id] = {
            'sender': data.get('from'),
            'filename': data.get('filename'),
            'filesize': data.get('filesize'),
            'chat_type': data.get('chat_type'),
            'chat_id': data.get('chat_id')  # could be sender or group
        }
        
        # Display the offer
        print(f"\n {data.get('from')} wants to send you {data.get('filename')} ({data.get('filesize')} bytes)")
        print(f"   Transfer ID: {transfer_id}")
        print("   Type: /accept <transfer_id> or /reject <transfer_id>")
        
        # If in chat mode, show prompt
        if self.chatting_mode:
            print(">> ", end="", flush=True)

    def send_message(self, recipient, message):
        print(f"send_message called, logged_in={self.logged_in}")
        if not self.logged_in:
            print("You must be logged in first")
            return
            
        self.on_user_input({
            "message_name": "MSG",
            "data": {
                "chat_id": recipient,
                "chat_type": "private",
                "payload": message
            }
        })
        print(f"Message sent to {recipient}")
        
    def clear(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_current(self):
        print(f"Chatting with {self.current_chat}")

    def process_self_message(self):
        print("\nYou can't message yourself! Please exit the chat.\n>>", end="")

    def process_incorrect_recipient(self):
        print("\nThis user does not exist! Please exit the chat.\n>>", end="")

    def process_incorrect_group(self):
        print("\nThis group not exist! Please exit the chat.\n>>", end="")

    def process_not_group_member(self):
        print("\nYou are not a member of this group! Please exit the chat.\n>>", end="")
    
    def process_shutdown(self):
        print("\nServer has shut down. Press Enter to exit.")
        self.quit()

    def on_file_received(self, filepath):
        print(f"[UDP] Transfer complete -> {filepath}")