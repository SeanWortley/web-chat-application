class Protocol:
    def __init__(self, server):
        self.server = server
        self.handlers = {
            "AUTH": self.handle_AUTH,
            "CREATE_ACCOUNT": self.handle_CREATE_ACCOUNT,
            "MSG": self.handle_MSG,
            "CREATE_GROUP": self.handle_CREATE_GROUP,
            "JOIN_GROUP": self.handle_JOIN_GROUP,
            "LEAVE_GROUP": self.handle_LEAVE_GROUP,
            "GROUP_LIST": self.handle_GROUP_LIST,
            "GROUP_MEMBERS": self.handle_GROUP_MEMBERS,
        }
    
        self.server.groups = {} #focused on the group, so what users are on which specific grp
        self.server.user_groups = {} #focused on the user, and names the group each user is in

    def handleIncoming(self, connection, clientMessage):
        messageName = clientMessage["message_name"]
        handler = self.handlers.get(messageName)
        if handler:
            handler(connection, clientMessage)
        else: 
            print(f"Unknown message: {clientMessage["message_name"]}")

    def handle_AUTH(self, connection, message):
        username = message["data"]["username"]
        hashed_pword = message["data"]["hashed_password"]
        if (username in self.server.userList) and hashed_pword == (self.server.userList[username]):
            connection.authenticated = True
            connection.loggedInAs = username
            self.AUTH_OK(connection)
        else:
            self.AUTH_FAIL(connection)

    def handle_CREATE_ACCOUNT(self, connection, message):
        username = message["data"]["username"]
        hashed_pword = message["data"]["hashed_password"]
        if (username not in self.server.userList):
            self.server.userList[username] = hashed_pword
            connection.authenticated = True
            connection.loggedInAs = username
            self.CREATE_ACCOUNT_OK(connection)
        else:
            self.CREATE_ACCOUNT_FAIL(connection)

    def handle_LOGOUT(self, connection, message):
        username = connection.loggedInAs
        connection.authenticated = True
        connection.loggedInAs = None
        self.LOGOUT_ACK(connection, username)

    def AUTH_OK(self, connection):
        welcome_message = f'Welcome back, {connection.loggedInAs}!'

        connection.sendJson({
            "message_name": "AUTH_OK", 
            "data": {
                "welcome_message": welcome_message}
                })

    def AUTH_FAIL(self, connection):
        error_message = "INCORRECT USERNAME OR PASSWORD"
        connection.sendJson({
            "message_name": "AUTH_FAIL",
            "data": {
                "error_code": error_message}
        })

    def CREATE_ACCOUNT_OK(self, connection):
        welcome_message = f"welcome new user, {connection.loggedInAs}!"

        connection.sendJson({
            "message_name": "CREATE_ACCOUNT_OK",
            "data": {
                "welcome_message": welcome_message}
        })

    def CREATE_ACCOUNT_FAIL(self, connection):
        error_message = "A user with that name already exists!"

        connection.sendJson({
            "message_name": "CREATE_ACCOUNT_FAIL",
            "data": {
                "error_message": error_message
            }
        })

    def LOGOUT_ACK(self, connection, username):
        if username:
            goodbye_message = f"Goodbye, {username}!"
        else:
            goodbye_message = "You are already logged out."

        connection.sendJson({
            "message_name": "LOGOUT_ACK",
            "data": {
                "goodbye_message": goodbye_message
                }
        })

    def handle_MSG(self, connection, message):
        #this is for when a message is sent, from both group instance and private chat instance
        if not connection.authenticated:
            self.bad_request_error(connection, "User isn't connected")
            return
        
        from_user = connection.loggedInAs
        chat_id = message.get("chat_id")  #eeither the username or the grp_id/name
        chat_type = message.get("chat_type") 
        msg_id = message.get("msg_id", "unknown")
        timestamp = message.get("timestamp", "unknown")
        payload = message.get("payload", "")
        
        if chat_type == "private":
            # we know it's a 1-to-1 chat therefore send to 1 person, get their dets
            recipient = chat_id
            recipient_conn = self.get_user_connection(recipient)
            
            if recipient_conn:
                # if the useer is connected this means their  onlinne, therefore we'll continue with the process of sending them the text
                self.forward_message(recipient_conn, from_user, chat_id, "private", msg_id, timestamp, payload)
                self.MSG_DELIVERED(connection, msg_id, [recipient])
            else:
                # if the user is offline, we'll just store their message
                self.MSG_STORED(connection, msg_id, [recipient])
                
        elif chat_type == "group":
            # need to check if group exists, if it does we'll continue to send the message with recepient being all the memebers in the group (list)
            group_name = chat_id
            
            if group_name not in self.server.groups:
                self.bad_request_error(connection, "Group doesn't exist")
                return
            
            if from_user not in self.server.groups[group_name]:
                self.bad_request_error(connection, "You're not in this group")
                return
            
            # Process to send to all memebers in the group
            recipients = []
            for member in self.server.groups[group_name]:
                if member != from_user:
                    member_conn = self.get_user_connection(member)
                    if member_conn:
                        self.forward_message(member_conn, from_user, group_name, "group", msg_id, timestamp, payload)
                        recipients.append(member)
            
            if recipients:
                self.MSG_DELIVERED(connection, msg_id, recipients)

    def handle_CREATE_GROUP(self, connection, message):
        if not connection.authenticated:
            self.bad_request_error(connection, "You aren't logged in")
            return
            
        group_name = message.get("group_name")
        username = connection.loggedInAs
        
        #to avoid duplicate group(names)
        if group_name in self.server.groups:
            self.CREATE_GROUP_NAK(connection, "fail", "Group already exists")
            return
        
        self.server.groups[group_name] = [username]  
        
        # This group will be added to the list of the user's groups their in
        if username not in self.server.user_groups:
            self.server.user_groups[username] = []
        self.server.user_groups[username].append(group_name)
        
        print(f" Group '{group_name}' created by {username}")
        self.CREATE_GROUP_ACK(connection, "success", f"Group '{group_name}' created!")

    def handle_JOIN_GROUP(self, connection, message):
        if not connection.authenticated:
            self.bad_request_error(connection, "User isn't logged in")
            return
            
        group_name = message.get("group_name")
        username = connection.loggedInAs
        
        if group_name not in self.server.groups:
            self.JOIN_GROUP_ACK(connection, "fail", "Group doesn't exist")
            return
        
        if username in self.server.groups[group_name]:
            self.JOIN_GROUP_ACK(connection, "fail", "Already in group")
            return
        
        self.server.groups[group_name].append(username)
        
        if username not in self.server.user_groups:
            self.server.user_groups[username] = []
        self.server.user_groups[username].append(group_name)
        
        print(f" {username} joined '{group_name}'")
        self.JOIN_GROUP_ACK(connection, "success", f"You joined '{group_name}'")

    def CREATE_GROUP_ACK(self, connection, result, message):
        connection.sendJson({
            "message_name": "CREATE_GROUP_ACK",
            "type": "CONTROL",
            "result": result,
            "message": message
        })

    def JOIN_GROUP_ACK(self, connection, result, message):
        connection.sendJson({
            "message_name": "JOIN_GROUP_ACK",
            "type": "CONTROL",
            "result": result,
            "message": message
        })

    def LEAVE_GROUP_ACK(self, connection, result, message):
        connection.sendJson({
            "message_name": "LEAVE_GROUP_ACK",
            "type": "CONTROL",
            "result": result,
            "message": message
        })
