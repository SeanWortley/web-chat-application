from threading import Thread, Event
from hashlib import sha256
from tokenize import group
import queue
import os
import json
from pathlib import Path

class Terminal:

    def __init__(self):
        self.commands = {
            "/help": self.displayHelp,
            "/login": self.login,
            "/register": self.register,
            "/logout": self.logout,
            "/msg": self.send_message,
            "/current": self.print_current
        }
        self.on_user_input = None
        self.wait_event = Event()
        self.running = True
        self.logged_in = False
        self.chatting_mode = False


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

            if text.startswith("/msg "):
                parts = text[5:].split(maxsplit=1)
                if len(parts) == 2:
                    recipient, message = parts
                    self.wait_event.clear()
                    self.send_message(recipient, message)
                    self.wait_event.wait()
                else:
                    print("Usage: /msg username message")
            elif text == "1": #Private chat
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
            return
    
        # Get the payload
        data = message.get("data", {})
        payload = data.get("payload")
        
        # Check if it's a media message (JSON)
        media_data = self.extract_media_payload(payload)
        
        if media_data:
            # It's a media message
            msg_type = media_data.get("type")
            sender = data.get("from")
            filename = media_data.get("filename")
            
            if msg_type == "MEDIA_OFFER":
                answer = input(f"{sender} wants to send you {filename}, do you Accept/Reject?")
                self.media_offer(message, media_data, answer)
            elif msg_type == "MEDIA_RESPONSE":
                self.media_response(message, media_data)
            elif msg_type == "MEDIA_COMPLETE":
                self.media_complete(message, filename)
            else:
                # Unknown media type
                print(f"Unknown media type: {msg_type}")
                self.print_msg(message)
        else:
            # It's a plain text message
            self.print_msg(message)

    def extract_media_payload(self, payload):
        # If it's already a dict, use it directly
        if isinstance(payload, dict):
            return payload
        
        # If it's a string, try to parse as JSON
        if isinstance(payload, str):
            # Quick check: does it look like JSON?
            payload_stripped = payload.strip()
            if payload_stripped.startswith('{') and payload_stripped.endswith('}'):
                try:
                    result = json.loads(payload)
                    if isinstance(result, dict):
                        return result
                except:
                    pass
        
        # Not a media message
        return None
    
    def media_offer(self, answer):
        self.media_response(answer)
    
    def media_response():
        # how do I send it to protocol to be handled
        pass

    def media_complete(self, filename):
         print(f"File transfer complete: {filename}")

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
        logs = self.database.get_private_chat_history(chat_id) #Dictionary
        for message in logs:
            from_user = message.get("from_user")
            msg_text = message.get("msg_text")
            sender = ">> " if (from_user == self.loggedInAs) else f"{from_user}: "
            print(sender + msg_text)
        print("-------------------------------------")
        
    def load_group_logs(self, chat_id):
        logs = self.database.get_group_chat_history(chat_id)
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
        print(f"Entered private chat room with {recipient}\n/exit to leave")
    
        self.load_private_logs(recipient)
            
        self.process_unread_in_current_chat()
        text = input(">> ")
        while text != "/exit":
            if text == "/mdt":
                filepath = input("Enter filepath:\n")
                self.initiate_media_transfer(recipient, filepath, chat_type= "private")
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
        self.show_logged_in_menu()

    def initiate_media_transfer(self, recipient, filepath, chat_type):
        # Validate path
        file_path = Path(filepath)
        if not file_path.exists():
            print(f"File not found: {filepath}")
            return
    
        filename = file_path.name
        filesize = file_path.stat().st_size

        media_request = {
            'type': 'MEDIA_OFFER',
            'filename': filename,
            'filesize': filesize,
        }

        self.on_user_input({
            "message_name": "MSG",
            "data": {
                "chat_id": recipient,
                "chat_type": chat_type,
                "payload": json.dumps(media_request)
            }
        })

    def start_group_chat(self):
        group = input("Which chat room would you like to enter?\n> ")
        self.current_chat = group

        self.chatting_mode = True
        print(f"Entered {group} chat room \n/exit to leave")

        self.load_group_logs(group)

        self.process_unread_in_current_chat()
        text = input(">> ")
        while text != "/exit":
            if text == "/mdt":
                filepath = input("Enter filepath:\n")
                self.initiate_media_transfer(group, filepath, chat_type="group")
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
        self.show_logged_in_menu()
    
    def resume(self):
        self.wait_event.set()
    
    def displayHelp(self):
        self.resume()
        pass # Implement later

    def show_logged_out_menu(self):
        self.clear()
        print("=== MAIN MENU ===")
        print("/login")
        print("/register")
        print("/help")

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
        self.on_user_input({
            "message_name": "LOGOUT"
        })

    def quit(self):
        self.running = False
        self.logout()
        self.on_user_input({
            "message_name": "close_connection"
        })
        self.on_user_input({
            "message_name": "quit_program"
        })

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