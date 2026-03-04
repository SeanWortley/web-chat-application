from threading import Thread, Event
from hashlib import sha256

class Terminal:

    def __init__(self):
        self.commands = {
            "/help": self.displayHelp,
            "/login": self.login,
            "/register": self.register,
            "/logout": self.logout,
            "2": self.create_group
        }
        self.on_user_input = None
        self.wait_event = Event()
        self.running = True

    def start(self):
        print("Welcome to the terminal interface for our chat application!")
        print("To get started, type '/login', or '/help' for a list of commands.")
        self.show_logged_out_menu()
        Thread(target=self.input_loop).start()

    def input_loop(self):
        while self.running:
            text = input("> ")

            if text in self.commands:
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
        print("4. Message Friend")
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

    def close(self):
        self.running = False
        self.logout()
        self.on_user_input({
            "message_name": "close_connection"
        })

    def create_group(self):
        group_name = input("Enter your desired group name:\n> ")
        members = []
        print("Add members to the group. Type 'done' when finished. Max 4 members.")
        
        while len(members) < 4:
            member = input(f"Member {len(members)+1}:\n> ")

            if member.lower() == "done":
                break

            if member in members:
                print(f"{member} is already in the group.")
                continue

            members.append(member)
        
        # Send group creation to server after finishing
        self.on_user_input({
            "message_name": "CREATE_GROUP",
            "data": {
                "group_name": group_name,
                "members": members,
            }
        })

    def display(self, text): # Will have to be adapted once GUI is added.
        print(text)
        