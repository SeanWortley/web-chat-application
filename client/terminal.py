from threading import Thread, Event
from hashlib import sha256
import os
import json

class Terminal:

    def __init__(self):
        self.commands = {
            "/help": self.displayHelp,
            "/login": self.login,
            "/register": self.register,
            "/logout": self.logout,
            "2": self.create_group, 
            "/msg": self.send_message,
            "/quit": self.quit,
            "1": self.view_groups,
            "2": self.create_group,
            "3": self.join_group,
            "4": self.share_media

        }
        self.on_user_input = None
        self.wait_event = Event()
        self.running = True
        self.logged_in = False

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
            elif text == "1":
                self.wait_event.clear()
                self.view_groups()
                self.wait_event.wait()
            elif text == "2":
                self.wait_event.clear()
                self.create_group()
                self.wait_event.wait()
            elif text == "3":
                self.wait_event.clear()
                self.join_group()
                self.wait_event.wait()
            elif text == "4":
                self.wait_event.clear()
                self.leave_group()
                self.wait_event.wait()
            elif text == "5":
                self.wait_event.clear()
                self.logout()
                self.wait_event.wait()
            elif text in self.commands:
                command = self.commands.get(text)
                self.wait_event.clear()
                command()
                self.wait_event.wait()
            else:
                print("Invalid command. Try /help")
            
    def resume(self):
        self.wait_event.set()
    
    def displayHelp(self):
        pass # Implement later

    def show_logged_out_menu(self):
        print("=== MAIN MENU ===")
        print("/login")
        print("/register")
        print("/help")

    def show_logged_in_menu(self):
        print("=== CHAT MENU ===")
        print("1. View Groups")
        print("2. Create Group")
        print("3. Join Group")
        print("4. Share media with Friend")
        print("5. Logout")

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
    
    def share_media(self):
        # A client must make a request before sending media
        recipient = input("Enter name of recepient:\n> ")
        filepath = input("Enter file path:\n> ")
        filename = os.path.basename(filepath)
        filesize = os.path.getSize(filepath)

        # Create media request payload
        media_offer = {
        'type': 'MEDIA_REQUEST',
        'filename': filename,
        'filesize': filesize,
        'sender': self.client.username,
        #'sender_udp_port': 
        }


        self.on_user_input({
            "message_name": "MSG",
            "data": {  
                "msg_type": "media", # to seperate whether we are dealing with text/media
                "chat_id": recipient,
                "chat_type": "private",
                "payload": json.dump(media_offer)
            }
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
        #print(f"Message sent to {recipient}")
        