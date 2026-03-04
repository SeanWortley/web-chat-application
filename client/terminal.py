from threading import Thread, Event
from hashlib import sha256

class Terminal:

    def __init__(self):
        self.commands = {
            "/help": self.displayHelp,
            "/login": self.login,
            "/register": self.register,
            "/logout": self.logout,
            "/close": self.close
        }

        self.on_user_input = None
        self.wait_event = Event()

    def start(self):
        print("Welcome to the terminal interface for our chat application!")
        print("To get started, type '/login', or '/help' for a list of commands.")
        Thread(target=self.input_loop).start()

    def input_loop(self):
        while True:
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
        self.logout()
        self.on_user_input({
            "message_name": "close"
        })

    def display(self, text): # Will have to be adapted once GUI is added.
        print(text)
        