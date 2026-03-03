class Protocol:
    def __init__(self, server):
        self.server = server
        self.handlers = {
            "AUTH": self.handle_AUTH,
            
        }

    def handleIncoming(self, connection, clientMessage):
        messageName = clientMessage["message_name"]
        handler = self.handlers.get(messageName)
        if handler:
            handler(connection, clientMessage)
        else: 
            print(f"Unknown message: {clientMessage["message_name"]}")

    def handle_AUTH(self, connection, message):
        username = message["username"]
        hashed_pword = message["hashed_password"]
        if (username in self.server.userList) and hashed_pword == (self.server.userList[username]):
            connection.authenticated = True
            connection.loggedInAs = username
            self.AUTH_OK(connection)
        else:
            self.AUTH_FAIL(connection)

    def AUTH_OK(self, connection):
        welcome_message = f'Welcome back, {connection.loggedInAs}!'

        connection.sendJson({
            "message_name": "AUTH_OK", 
            "data": {"welcome_message": welcome_message}
                })

    def AUTH_FAIL(self, connection):
        error_code = "INCORRECT USERNAME OR PASSWORD"
        connection.sendJson({
            "message_name": "AUTH_FAIL",
            "data": {"error_code": error_code}
        })