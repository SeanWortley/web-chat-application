from threading import Thread

class Terminal:
    validCommands = ["/login", "/register", "/logout"]

    def __init__(self):
        self.on_user_input = None

    def start(self):
        print("Welcome to the terminal interface for our chat application!")
        print("To get started, type '/login', or '/help' for a list of commands.")
        Thread(target=self.input_loop).start()

    def input_loop(self):
        while True:
            text = input("> ")

            if text == "/help":
                self.displayHelp()

            elif text in self.validCommands:
                self.on_user_input(text)

            else: 
                print("Invalid command. Try /help")
            
    def displayHelp(self):
        pass # Implement later
        