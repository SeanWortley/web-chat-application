from hashlib import sha256

class Protocol:
    def __init__(self, client):
        self.client = client
        self.handlers = {
            "AUTH_OK": self.handle_AUTH_OK,
            "AUTH_FAIL": self.handle_AUTH_FAIL,
            "CREATE_ACCOUNT_OK": self.handle_CREATE_ACCOUNT_OK,
            "CREATE_ACCOUNT_FAIL": self.handle_CREATE_ACCOUNT_FAIL,
            "LOGOUT_ACK": self.handle_LOGOUT_ACK,
        }

    def handleIncoming(self, connection, serverMessage):
        messageName = serverMessage["message_name"]
        handler = self.handlers.get(messageName)
        if handler:
            handler(connection, serverMessage)

        else: 
            self.client.interface.display(f"Unknown message: {serverMessage["message_name"]}")
        self.client.interface.resume()

    def handle_AUTH_OK(self, connection, message):
        self.client.authenticated = True
        self.client.username = True

        self.client.interface.display(message["data"]["welcome_message"])
        self.client.interface.display("Login successful!")
        self.client.interface.menu.show_logged_in_menu()
        self.client.interface.resume()

    def handle_AUTH_FAIL(self, connection, message):
        self.client.interface.display(f"Failed to authenticate: {message["data"]["error_code"]}")
        self.client.interface.menu.show_logged_out_menu()
        self.client.interface.resume()

    def handle_CREATE_ACCOUNT_OK(self, connection, message):
        self.client.interface.display(message["data"]["welcome_message"])
        self.client.interface.menu.show_logged_in_menu()
        self.client.interface.resume()

    def handle_CREATE_ACCOUNT_FAIL(self, connection, message):
        self.client.interface.display(message["data"]["error_message"])
        self.client.interface.menu.show_logged_out_menu()
        self.client.interface.resume()

    def handle_LOGOUT_ACK(self, connection, message):
        self.client.interface.display(message["data"]["goodbye_message"])
        self.client.authenticated = False
        self.client.loggedInAs = None
        # What happens after the logout
    def AUTH(self, connection, username, hashed_pword):
        connection.sendJson({
            "message_name": "AUTH",
            "data": {
                "username": username,
                "hashed_password": hashed_pword
            }
        })

    def CREATE_ACCOUNT(self, connection, username, hashed_pword):
        connection.sendJson({
            "message_name": "CREATE_ACCOUNT",
            "data": {
                "username": username,
                "hashed_password": hashed_pword
            }
        })

    def CREATE_GROUP(self, connection, groupname, members):
        connection.sendJson({
            "message_name": "CREATE_GROUP",
            "data": {
                "group_name": groupname,
                "members": members
            }
        })
    def JOIN_GROUP(self, connection, username, groupname):
        connection.sendJson({
            "message_name": "JOIN_GROUP",
            "data": {
                "username": username,
                "group_name": groupname
            }
        })

    def LOGOUT(self, connection):
        connection.sendJson({
            "message_name": "LOGOUT"
        })

