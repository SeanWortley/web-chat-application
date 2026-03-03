from hashlib import sha256

class Protocol:
    def __init__(self, client):
        self.client = client
        self.handlers = {
            "AUTH_OK": self.handle_AUTH_OK,
            "AUTH_FAIL": self.handle_AUTH_FAIL,
            "LOGOUT_ACK": self.handle_LOGOUT_ACK,
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
        else:
            self.Create_ACCOUNT(self, connection)


    def handle_CREATE_ACCOUNT_OK(self, connection, message):
        print(message["welcome_message"])

    def handle_CREATE_ACCOUNT_FAIL(self, connection, message):
        print(message["error_message"])
        choice = input("Would you like to try again? (Yes/No)\n")
        if (choice.lower() == "yes") or (choice.lower() == "y"):
            self.CREATE_ACCOUNT(connection)
        else:
            connection.close()

    def handle_LOGOUT_ACK(self, connection, message):
        print(message["goodbye_message"])
        self.client.authenticated = False
        self.client.loggedInAs = None

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

    def LOGOUT(self, connection):
        connection.sendJson({
            "message_name": "LOGOUT"
        })

