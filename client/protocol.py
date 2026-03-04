from hashlib import sha256

class Protocol:
    def __init__(self, client):
        self.client = client
        self.handlers = {
            "AUTH_OK": self.handle_AUTH_OK,
            "AUTH_FAIL": self.handle_AUTH_FAIL
        }

    def handleIncoming(self, connection, serverMessage):
        messageName = serverMessage["message_name"]
        handler = self.handlers.get(messageName)
        if handler:
            handler(connection, serverMessage)
        else: 
            print(f"Unknown message: {serverMessage["message_name"]}")

    def handle_AUTH_OK(self, connection, message):
        self.client.authenticated = True
        self.client.username = True

        print(message["data"]["welcome_message"])
    
    def handle_AUTH_FAIL(self, connection, message):
        print(f"Failed to authenticate: {message["data"]["error_code"]}")

        choice = input("Would you like to try again? (Yes/No)\n")
        if (choice.lower() == "yes") or (choice.lower() == "y"):
            self.AUTH(connection)

    def AUTH(self, connection):
        username = input("Enter your username: ")
        hashed_pword = (sha256(input("Enter your password: ").encode())).hexdigest()
        
        connection.sendJson({
            "message_name": "AUTH",
            "username": username,
            "hashed_password": hashed_pword
        })

    def CREATE_ACCOUNT(self, connection):
        username = input("Enter your desired username: ")
        hashed_pword = (sha256(input("Enter your desired password: ").encode())).hexdigest()

        connection.sendJson({
            "message_name": "CREATE_ACCOUNT",
            "username": username,
            "hashed_password": hashed_pword
        })

    def handle_CREATE_ACCOUNT_FAIL():
        pass
        
    def CREATE_GROUP(self, connection, group_name):
        connection.sendJson({
            "message_name": "CREATE_GROUP",
            "type": "COMMAND",
            "group_name": group_name
        })
        print(f"Requesting to create group: {group_name}")

    def JOIN_GROUP(self, connection, group_name):
        connection.sendJson({
            "message_name": "JOIN_GROUP",
            "type": "COMMAND",
            "group_name": group_name
        })
        print(f" Requesting to join group: {group_name}")

    def LEAVE_GROUP(self, connection, group_name):
        connection.sendJson({
            "message_name": "LEAVE_GROUP",
            "type": "COMMAND",
            "group_name": group_name
        })
        print(f"Requesting to leave group: {group_name}")

    def MSG(self, connection, chat_id, chat_type, text):
        msg_id = f"msg_{int(time.time())}"
        timestamp = time.time()
        
        connection.sendJson({
            "message_name": "MSG",
            "type": "DATA",
            "from": self.client.username,
            "chat_id": chat_id,
            "chat_type": chat_type,
            "msg_id": msg_id,
            "timestamp": timestamp,
            "payload": text
        })
    