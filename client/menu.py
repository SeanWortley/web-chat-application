class Menu:

    def __init__(self, terminal):
        self.terminal = terminal

    def show_logged_out_menu(self):
        self.terminal.display("=== MAIN MENU ===")
        self.terminal.display("/login")
        self.terminal.display("/register")
        self.terminal.display("/help")

    def show_logged_in_menu(self):
        self.terminal.display("=== CHAT MENU ===")
        self.terminal.display("1. View Groups")
        self.terminal.display("2. Create Group")
        self.terminal.display("3. Join Group")
        self.terminal.display("4. Message Friend")
        self.terminal.display("5. Logout")

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
        self.terminal.on_user_input({
            "message_name": "CREATE_GROUP",
            "data": {
                "group_name": group_name,
                "members": members,
            }
        })