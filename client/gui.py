# client/gui.py
from pydoc import text
from pydoc import text
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
from hashlib import sha256
import queue
import database

class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chat Application")
        self.root.geometry("600x500")
        
        self.on_user_input = None
        self.running = True
        self.logged_in = False
        self.loggedInAs = None
        self.current_chat = None
        self.chatting_mode = False
        
        # Queue for thread-safe message passing
        self.message_queue = queue.Queue()
        
        # Unread messages storage
        self.unread_messages = {}
        self.chat_windows = {}  # Track open chat windows
        
    def start(self):
        # After prompting  it in the terminal, this will start the GUI and show the login screen.  
        # The process_queue method will be called every 100ms to check for messages from other threads and update the GUI accordingly.
        # Show login screen first
        self.show_login_screen()
        # Start the message queue so we see new messages/notifications in the main window
        self.process_queue()
        # The main loop will run until the user closes the window.
        self.root.mainloop()
        
    def process_queue(self):
        # This method is called using after() to check the message queue for any updates that need to be reflected in the GUI.
        try:
            while True:
                msg = self.message_queue.get_nowait()
                if msg["type"] == "display":
                    self._display_text(msg["text"])
                elif msg["type"] == "message":
                    self._handle_incoming_message(msg["data"])
                elif msg["type"] == "unsent":
                    self._handle_unsent_messages(msg["data"])
        except queue.Empty:
            pass
        finally:
            # Check again after 100ms
            self.root.after(100, self.process_queue)
    
    def _display_text(self, text):
        """Display text in the main window"""
        if hasattr(self, 'output_area'):
            self.output_area.insert(tk.END, text + "\n")
            self.output_area.see(tk.END)
    
    def show_login_screen(self):
        # This will display the login screen where users can enter their username and password to either log in or register a new account.
        for widget in self.root.winfo_children():
            widget.destroy()
        
        frame = tk.Frame(self.root, padx=30, pady=30)
        frame.pack(expand=True)
        
        tk.Label(frame, text="Welcome to your Chat App. What are we chatting about today?", font=("Helvetica", 16)).pack(pady=10)
        
        tk.Label(frame, text="Username:").pack()
        self.login_username = tk.Entry(frame, width=30)
        self.login_username.pack(pady=5)
        
        tk.Label(frame, text="Password:").pack()
        # Showing - instead of actual characters for password entry as a means of basic security
        self.login_password = tk.Entry(frame, width=30, show="-")
        self.login_password.pack(pady=5)
        
        btn_frame = tk.Frame(frame)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Login", command=self.login, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Register", command=self.register, width=10).pack(side=tk.LEFT, padx=5)
    
    def show_main_menu(self):
        # Display the chat menu after the user has successfully logged in. 
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.current_chat = None  # Reset current chat
        self.chatting_mode = False

        menu_frame = tk.Frame(self.root, padx=20, pady=20)
        menu_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        tk.Label(menu_frame, text=f"Logged in as: {self.loggedInAs}", font=("Arial", 10)).pack(pady=5)
        tk.Label(menu_frame, text="MAIN MENU", font=("Arial", 14, "bold")).pack(pady=10)
        
        buttons = [
            ("1. Private Chat", self.start_private_chat),
            ("2. Group Chat", self.start_group_chat),
            ("3. View Groups", self.view_groups),
            ("4. Create Group", self.create_group),
            ("5. Join Group", self.join_group),
            ("Logout", self.logout)
        ]
        
        for text, command in buttons:
            tk.Button(menu_frame, text=text, command=command, width=20, pady=5).pack(pady=2)
        
        # This will be the display box that shows incoming messages. It will be updated by the process_queue method whenever a new message arrives or when the user receives a notification about unread messages.
        self.output_area = scrolledtext.ScrolledText(self.root, width=40, height=25, state='normal')
        self.output_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def login(self):
        # When the user clicks the login button, this method will be called. It will hash the password using SHA-256 and then send the login information to the server using the on_user_input callback. 
        username = self.login_username.get()
        password = self.login_password.get()
        # Wont allow empty username or password to be sent to the server, and will show an error message instead.
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return
        
        hashed = sha256(password.encode()).hexdigest()
        self.loggedInAs = username
        
        # Use after() to ensure we're in the main thread
        if self.on_user_input:
            self.root.after(100, lambda: self._send_login(username, hashed))
    
    def _send_login(self, username, hashed):
        # Sends the login information to the server. It uses the on_user_input callback to send a message with the username and hashed password.
        if self.on_user_input:
            self.on_user_input({
                "message_name": "AUTH",
                "data": {
                    "username": username,
                    "hashed_password": hashed
                }
            })
    
    def register(self):
        # Similar to the login method, this will be called when the user clicks the register button. It will also hash the password and send the new user's details to the server.
        username = self.login_username.get()
        password = self.login_password.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter username and password")
            return
        
        hashed = sha256(password.encode()).hexdigest()
        self.loggedInAs = username
        
        if self.on_user_input:
            self.root.after(100, lambda: self._send_register(username, hashed))
    
    def _send_register(self, username, hashed):
        # This method sends the registration information to the server. It uses the on_user_input callback to send a message with the username and hashed password for account creation.
        if self.on_user_input:
            self.on_user_input({
                "message_name": "CREATE_ACCOUNT",
                "data": {
                    "username": username,
                    "hashed_password": hashed
                }
            })
    
    def start_private_chat(self):
        # This method will be called when the user clicks the "Private Chat" button. It will prompt the user to enter the username of the person they want to chat with and then open a new chat window for that private conversation.
        recipient = simpledialog.askstring("Private Chat", "Enter username of the person you want to chat with:")
        # If the user cancels the prompt or leaves it empty, we simply return without doing anything. 
        if not recipient:
            return
        # Sets the current chat to the recipient's username and will open a new chat window for this private conversation. This is where sender types and receives messages from this specific user.
        self.current_chat = recipient
        self.open_chat_window(recipient, "private")
        self.load_private_logs(recipient)

    def load_private_logs(self, chat_id):
        logs = self.database.get_private_chat_history(chat_id)
        for message in logs:
            from_user = message.get("from_user")
            msg_text = message.get("msg_text")
            sender = "You: " if (from_user == self.loggedInAs) else f"{from_user}: "
    
    def start_group_chat(self):
        # Similar to the start_private_chat method, this will be called when the user clicks the "Group Chat" button. It will prompt the user to enter the name of the group they want to chat in and then open a new chat window for that group conversation.
        group = simpledialog.askstring("Group Chat", "Enter group name you want to join:")
        # If the user cancels the prompt or leaves it empty, we simply return without doing anything.
        if not group:
            return
        # Sets the current chat to the group name and will open a new chat window for this group conversation. 
        self.current_chat = group
        self.open_chat_window(group, "group")
    
    def open_chat_window(self, chat_id, chat_type):
        # Opens a new chat window for either a private or group chat. It takes the chat_id (username = private chats and the group name = group chats).
        if chat_id in self.chat_windows:
            self.chat_windows[chat_id].lift()
            self.current_chat = chat_id
            return
        
        window = tk.Toplevel(self.root)
        window.title(f"{'Private' if chat_type == 'private' else 'Group'} Chat: {chat_id}")
        window.geometry("500x400")
        
        # Store reference to this chat window so we can update it with new messages or show notifications if there are unread messages for this chat.
        self.chat_windows[chat_id] = window
        self.current_chat = chat_id

        # This where the messags will actually be displayed in the chat window.
        chat_display = scrolledtext.ScrolledText(window, width=60, height=20, state='normal')
        chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # This us where any unread messages for this chat will be displayed.
        if chat_id in self.unread_messages:
            for msg in self.unread_messages[chat_id]:
                from_user = msg.get("from")
                payload = msg.get("payload")
                chat_display.insert(tk.END, f"{from_user}: {payload}\n")
            del self.unread_messages[chat_id]
        
        # Input area where the user can type their message and send it to either the private chat recipient or the group chat. 
        input_frame = tk.Frame(window)
        input_frame.pack(fill=tk.X, padx=10, pady=5)
        # entry allows the user to type their message, and the send button will trigger the send_chat_message method to send the message to the server and display it in the chat window.
        entry = tk.Entry(input_frame)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        entry.bind("<Return>", lambda e: self.send_chat_message(entry, chat_id, chat_type, chat_display))
        
        send_btn = tk.Button(input_frame, text="Send", 
                            command=lambda: self.send_chat_message(entry, chat_id, chat_type, chat_display))
        send_btn.pack(side=tk.RIGHT, padx=5)
        
        # When the user closes the chat window, we romove it from the chat_windows dictionary.
        def on_close():
            if chat_id in self.chat_windows:
                del self.chat_windows[chat_id]
            if self.current_chat == chat_id:
                self.current_chat = None
            window.destroy()
        
        window.protocol("WM_DELETE_WINDOW", on_close)
    
    def send_chat_message(self, entry, chat_id, chat_type, display):
    # Triggered when the user clicks the send button or presses Enter in the chat input field.
        text = entry.get()
        if not text:
            return
    
    # Make sure current_chat is set to this chat
        self.current_chat = chat_id
    
    # Displays the sent message immediately in the chat window for the user to see.
        display.insert(tk.END, f"You: {text}\n")
        display.see(tk.END)
        entry.delete(0, tk.END)
    
    # Sends the message to the server using the on_user_input callback.
        if self.on_user_input:
            self.on_user_input({
                "message_name": "MSG",
                "data": {
                    "chat_id": chat_id,
                    "chat_type": chat_type,
                    "payload": text
                }
            })

    def view_groups(self):
        # Triggered when the user clicks the "View Groups" button. A request will be sent to the server to get the list of groups that the user is a member of, and then display that list in a message box.
        if self.on_user_input:
            self.on_user_input({
                "message_name": "GROUP_LIST"
            })
    
    def create_group(self):
        # Triggered when the user clicks the "Create Group" button. It will prompt the user to enter a name for the new group they want to create, and then send that information to the server to create the group.
        group = simpledialog.askstring("Create Group", "Enter group name:")
        if group and self.on_user_input:
            self.on_user_input({
                "message_name": "CREATE_GROUP",
                "data": {"group_name": group}
            })
    
    def join_group(self):
        # Triggered when the user clicks the "Join Group" button. It will prompt the user to enter the name of the group they want to join, and then send that information to the server to request to join the group.
        group = simpledialog.askstring("Join Group", "Enter group name:")
        if group and self.on_user_input:
            self.on_user_input({
                "message_name": "JOIN_GROUP",
                "data": {"group_name": group}
            })
    
    def logout(self):
       # Triggered when the user clicks the "Logout" button. It will send a logout message to the server and then return the user to the login screen.
        if self.on_user_input:
            self.on_user_input({"message_name": "LOGOUT"})
        self.logged_in = False
        self.root.after(0, self.show_login_screen)
    
    def display(self, text):
        self.message_queue.put({"type": "display", "text": text})
    
    def process_msg(self, message, channel):
        # Called by the client when a new message is received from the server.
        self.message_queue.put({"type": "message", "data": message})
    
    def _handle_incoming_message(self, message):
    # Processes incoming messages and determines where to display them.
        data = message.get("data", {})
        from_user = data.get("from")
        chat_id = data.get("chat_id")
        chat_type = data.get("chat_type")
        payload = data.get("payload")
    
    # Determine which chat this message belongs to based on the chat type.
        if chat_type == "private":
            target_chat = from_user  # For private messages, the chat is identified by the sender
        else:
            target_chat = chat_id  # For group messages, use the group name
    
    # If chat window is open, show message there
        if target_chat in self.chat_windows:
            window = self.chat_windows[target_chat]
        
        # Find the ScrolledText widget in the window
            for child in window.winfo_children():
                if isinstance(child, scrolledtext.ScrolledText):
                    child.insert(tk.END, f"{from_user}: {payload}\n")
                    child.see(tk.END)
                    return
        # Also try to find it in nested frames
            for child in window.winfo_children():
                if isinstance(child, tk.Frame):
                    for grandchild in child.winfo_children():
                        if isinstance(grandchild, scrolledtext.ScrolledText):
                            grandchild.insert(tk.END, f"{from_user}: {payload}\n")
                            grandchild.see(tk.END)
                            return
    
        # Otherwise store as unread
        if target_chat not in self.unread_messages:
            self.unread_messages[target_chat] = []
    
        self.unread_messages[target_chat].append({
            "from": from_user,
            "payload": payload
    })
    
    # Show notification in main window
        if hasattr(self, 'output_area'):
            notification = f"\n New message from {from_user}"
            if chat_type == "group":
                notification = f"\n New message in {chat_id} from {from_user}"
            self.output_area.insert(tk.END, notification + "\n")
            self.output_area.see(tk.END)
    
    def process_unsent_batch(self, groups):
        #Puts unsent messages into the message queue to be processed in the main thread.
        self.message_queue.put({"type": "unsent", "data": groups})
    
    def _handle_unsent_messages(self, groups):
        for chat_id, messages in groups.items():
            for msg in messages:
                # Queue them as regular messages
                fake_msg = {
                    "data": {
                        "from": msg["sender"],
                        "chat_id": chat_id,
                        "chat_type": msg["chat_type"],
                        "payload": msg["content"]
                    }
                }
                self._handle_incoming_message(fake_msg)
    
    def resume(self):
        pass
    
    def show_logged_in_menu(self):
       # display the main menu after the user has successfully logged in. It sets the logged_in flag to True and then calls the show_main_menu method to update the GUI to show the main menu options.
        self.logged_in = True
        self.root.after(0, self.show_main_menu)
    
    def show_logged_out_menu(self):
        self.root.after(0, self.show_login_screen)