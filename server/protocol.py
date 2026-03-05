from tabnanny import verbose


class Protocol:
    def __init__(self, server):
        self.server = server
        self.handlers = {
            "AUTH": self.handle_AUTH,
            "CREATE_ACCOUNT": self.handle_CREATE_ACCOUNT,
            "LOGOUT": self.handle_LOGOUT,  
            "MSG": self.handle_MSG,
            "CREATE_GROUP": self.handle_CREATE_GROUP,
            "JOIN_GROUP": self.handle_JOIN_GROUP,
            "GROUP_LIST": self.handle_GROUP_LIST
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

        user = self.server.database.get_user(username)
        if (user and hashed_pword == user["hashed_password"]):
            connection.authenticated = True
            connection.loggedInAs = username
            self.AUTH_OK(connection)
        else:
            self.AUTH_FAIL(connection)

    def handle_CREATE_ACCOUNT(self, connection, message):
        username = message["data"]["username"]
        hashed_pword = message["data"]["hashed_password"]

        user = self.server.database.get_user(username)
        if (not user):
            self.server.database.create_user(username, hashed_pword)
            connection.authenticated = True
            connection.loggedInAs = username
            self.CREATE_ACCOUNT_OK(connection)
        else:
            self.CREATE_ACCOUNT_FAIL(connection)

    def handle_LOGOUT(self, connection, message):
        username = connection.loggedInAs
        connection.authenticated = False
        connection.loggedInAs = None
        self.LOGOUT_ACK(connection, username)

    def AUTH_OK(self, connection):
        welcome_message = f'Welcome back, {connection.loggedInAs}!'

        connection.sendJson({
            "message_name": "AUTH_OK", 
            "from": connection.loggedInAs,
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
            "from": connection.loggedInAs, 
            "data": {
                "welcome_message": welcome_message}
        })

    # Removed Sande's handling group creation, join, leave
    """
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
    """

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
        
        from_user = message.get("from")
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
        print(f"handle_CREATE_GROUP called with: {message}")
        if not connection.authenticated:
            self.CREATE_GROUP_ACK(connection, "fail", "You aren't logged in")

        group_name = message["data"]["group_name"]
        username = connection.loggedInAs
        
        #to avoid duplicate group(names)
        if self.server.database.get_group(group_name):
            self.CREATE_GROUP_ACK(connection, "fail", "Group already exists")
            return
        
        self.server.database.create_group(group_name, username)
        self.server.log(f"Group '{group_name}' created by {username}")

        # This group will be added to the list of the user's groups their in
        self.CREATE_GROUP_ACK(connection, "success", f"Group '{group_name}' created!")

    def handle_JOIN_GROUP(self, connection, message):
        if not connection.authenticated:
            self.JOIN_GROUP_ACK(connection, "fail", "You aren't logged in")
            return

        group_name = message["data"]["group_name"]
        username = connection.loggedInAs

        if not self.server.database.get_group(group_name):
            self.JOIN_GROUP_ACK(connection, "fail", "Group does not exist")
            return

        if self.server.database.is_group_member(group_name, username):   
            self.JOIN_GROUP_ACK(connection, "fail", f"Already in group {group_name}")
            return

        self.server.database.add_group_member(group_name, username)
        self.server.log(f"{username} joined '{group_name}'")
        self.JOIN_GROUP_ACK(connection, "success", f"You joined '{group_name}'")

    def handle_GROUP_LIST(self, connection, message):
        if not connection.authenticated:
            self.GROUP_LIST_ACK(connection, "fail", [], f"You aren't logged in")
            return

        username = connection.loggedInAs
        groups = self.server.database.get_user_groups(username)
        group_names = [row["group_name"] for row in groups]

        self.GROUP_LIST_ACK(connection, "success", group_names, None)

    def GROUP_LIST_ACK(self, connection, result, groups, message):
        connection.sendJson({
            "message_name": "GROUP_LIST_ACK",
            "data": {
                "result": result,
                "groups": groups,
                "message": message
            }
        })

    def CREATE_GROUP_ACK(self, connection, result, message):
        connection.sendJson({
            "message_name": "CREATE_GROUP_ACK",
            "data": {
                "result": result,
                "message": message
            }
        })

    def JOIN_GROUP_ACK(self, connection, result, message):
        connection.sendJson({
            "message_name": "JOIN_GROUP_ACK",
            "data": {
                "result": result,
                "message": message
            }
        })

    def LEAVE_GROUP_ACK(self, connection, result, message):
        connection.sendJson({
            "message_name": "LEAVE_GROUP_ACK",
            "data": {
                "result": result,
                "message": message
            }
        })
    def get_user_connection(self, username):
        ##will ID the user with their username, therefore for the message sending we the different users' terminals can operate correctly identifying these
        for conn in self.server.connections:
            if conn.loggedInAs == username and conn.authenticated:
                return conn
        return None
    
    def forward_message(self, recipient_conn, from_user, chat_id, chat_type, msg_id, timestamp, payload):
            #forarding of the message to correct recepient
            recipient_conn.sendJson({
            "message_name": "MSG",
            "type": "DATA",
            "data": {
            "from": from_user,
            "chat_id": chat_id,
            "chat_type": chat_type,
            "msg_id": msg_id,
            "timestamp": timestamp,
            "payload": payload
            }
    })
