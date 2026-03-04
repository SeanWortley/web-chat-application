class Protocol:
    def __init__(self, server):
        self.server = server
        self.handlers = {
            "AUTH": self.handle_AUTH,
            "CREATE_ACCOUNT": self.handle_CREATE_ACCOUNT,
            "LOGOUT": self.handle_LOGOUT,  
            "CREATE_GROUP": self.handle_CREATE_GROUP,
            "CREATE_GROUP_ACK": self.handle_CREATE_GROUP_ACK,  
            "JOIN_GROUP": self.handle_JOIN_GROUP,  
            "LEAVE_GROUP": self.handle_LEAVE_GROUP, 
            "MSG": self.handle_MSG,      
        }

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

    def handle_CREATE_GROUP(self, connection, message):
        group_name = message["data"]["group_name"]
        members = message["data"]["members"]  
        # Prevent duplicate group names
        if group_name in self.server.groups:
            self.CREATE_GROUP_FAIL(connection, "A group with that name already exists!")
            return

       # Validate members exist
        valid_members = [m for m in members if m in self.server.userList]

        if connection.loggedInAs not in valid_members:
            valid_members.append(connection.loggedInAs)

        self.server.groups[group_name] = valid_members

        # Notify all members currently online
        for username in valid_members:
            member_conn = self.server.get_connection_by_username(username)
            if member_conn:
                member_conn.sendJson({
                   "message_name": "CREATE_GROUP_ACK",
                   "data": {
                      "group_name": group_name,
                      "members": valid_members,
                      "message": f"You have been added to group '{group_name}'!"
                }
            })

            print(f"Group '{group_name}' created with members: {valid_members}")
    
    def CREATE_GROUP_FAIL(self, connection, error_message):
        connection.sendJson({
        "message_name": "CREATE_GROUP_FAIL",
        "data": {"error_message": error_message}
    })

    def handle_JOIN_GROUP(self, connection, message):
        group_name = message["data"]["group_name"]
        if group_name not in self.server.groups:
            connection.sendJson({
                "message_name": "JOIN_GROUP_FAIL",
                "data": {"error": "Group does not exist."}
            })
            return

        if connection.loggedInAs not in self.server.groups[group_name]:
            self.server.groups[group_name].append(connection.loggedInAs)

        connection.sendJson({
            "message_name": "JOIN_GROUP_ACK",
            "data": {"group_name": group_name}
            })

    def handle_LEAVE_GROUP(self, connection, message):
        group_name = message["data"]["group_name"]
        if group_name in self.server.groups and connection.loggedInAs in self.server.groups[group_name]:
            self.server.groups[group_name].remove(connection.loggedInAs)
            connection.sendJson({
                "message_name": "LEAVE_GROUP_ACK",
                "data": {"group_name": group_name}
            })

    def handle_CREATE_GROUP_ACK(self, message):
        group_name = message["data"]["group_name"]
        members = message["data"]["members"]

        self.terminal.display(f"Group '{group_name}' created successfully!")
        self.terminal.display(f"Members: {', '.join(members)}")

        self.terminal.resume()

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
        if not connection.authenticated:
         return
    
        from_user = connection.loggedInAs

        chat_id = message.get("chat_id")  
        chat_type = message.get("chat_type")  
        msg_id = message.get("msg_id") 
        timestamp = message.get("timestamp")  
        payload = message.get("payload")
    
        if chat_type == "private":
       
            recipient = chat_id
            recipient_conn = self.server.get_connection_by_username(recipient)
        
            if recipient_conn:
                recipient_conn.sendJson({
                    "message_name": "MSG",
                    "data": {
                    "from": from_user,
                    "chat_id": chat_id,
                    "chat_type": chat_type,
                    "msg_id": msg_id,
                    "timestamp": timestamp,
                    "payload": payload
                }
            })
            
            connection.sendJson({
                "message_name": "MSG_DELIVERED",
                "data": {
                    "message_id": msg_id,
                    "recipients": [recipient]
                }
            })
    
        elif chat_type == "group":
        # Message will be sent to all group members
            if chat_id in self.server.groups:
                for member in self.server.groups[chat_id]:
                    if member != from_user:
                        member_conn = self.server.get_connection_by_username(member)
                        if member_conn:
                            member_conn.sendJson({
                            "message_name": "MSG",
                            "data": {
                                "from": from_user,
                                "chat_id": chat_id,
                                "chat_type": chat_type,
                                "msg_id": msg_id,
                                "timestamp": timestamp,
                                "payload": payload
                            }
                        })

    