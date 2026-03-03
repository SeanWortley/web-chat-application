class Menu:

    def __init__(self, terminal):
        self.terminal = terminal

    def show_logged_out_menu(self):
        self.terminal.display("=== MAIN MENU ===")
        self.terminal.display("/login")
        self.terminal.display("/register")

    def show_logged_in_menu(self):
        self.terminal.display("=== CHAT MENU ===")
        self.terminal.display("1. Send Message")
        self.terminal.display("2. View Users")
        self.terminal.display("3. Logout")