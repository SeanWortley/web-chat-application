from tabnanny import verbose
import threading
import time


class Protocol:
    def __init__(self, server):
        self.server = server
        self.pending_offers = {} #
        self.lock = threading.Lock()
        self.handlers = {
            "AUTH": self.handle_AUTH,
            "CREATE_ACCOUNT": self.handle_CREATE_ACCOUNT,
            "LOGOUT": self.handle_LOGOUT,  
            "MSG": self.handle_MSG,
            "CREATE_GROUP": self.handle_CREATE_GROUP,
            "JOIN_GROUP": self.handle_JOIN_GROUP,
            "GROUP_LIST": self.handle_GROUP_LIST,
            "REQUEST_UNSENT_MESSAGES": self.handle_REQUEST_UNSENT_MESSAGES,
            "MEDIA_OFFER": self.handle_MSG
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

    def handle_REQUEST_UNSENT_MESSAGES(self, connection, message):
        if not connection.authenticated:
            return
        
        username = connection.loggedInAs
        messages = self.server.database.get_offline_messages(username)

        if not messages:
            return
        
        groups = {}

        for row in messages:
            key = row["group_id"] if row["chat_type"] == "group" else row["sender"]
            
            if key not in groups:
                groups[key] = []
            groups[key].append({
                "msg_id": row["msg_id"],
                "sender": row["sender"],
                "chat_type": row["chat_type"],
                "content": row["msg_text"],
                "timestamp": row["timestamp"]
            })
            
        self.UNSENT_MESSAGES(connection, groups)

        self.server.database.delete_offline_messages(username)
    
    def UNSENT_MESSAGES(self, connection, groups):
        connection.sendJson({
            "message_name": "UNSENT_MESSAGES",
            "data": {
                "groups": groups
            }
        })

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
        """
        Handles all incoming messages (private or group) and routes
        them to the correct handler based on message type.
        """
        if not connection.authenticated:
            self.bad_request_error(connection, "User isn't connected")
            return

        # Safely parse message data
        message_name = message.get("message_name")
        data = message.get("data", {})

        # Build a unified context for routing
        context = {
            # Core info
            "from_user": data.get("from"),
            "chat_id": data.get("chat_id"),  # username or group name
            "chat_type": data.get("chat_type"),

            # Text message fields
            "msg_id": data.get("msg_id", "unknown"),
            "timestamp": data.get("timestamp", "unknown"),
            "payload": data.get("payload", ""),

            # Media message fields
            "transfer_id": data.get("transfer_id"),
            "filename": data.get("filename"),
            "filesize": data.get("filesize"),
            "sender_port": data.get("sender_port")
        }

        # Handle private messages
        if context["chat_type"] == "private":
            recipient = context["chat_id"]
            recipient_conn = self.get_user_connection(recipient)
            context.update({
                "target_conn": recipient_conn,
                "recipient": recipient,
                "group_name": None
            })

            self.route_message(message_name, context)

        # Handle group messages
        elif context["chat_type"] == "group":
            group_name = context["chat_id"]

            # Validate group and membership
            if not self.server.database.get_group(group_name):
                self.bad_request_error(connection, "Group doesn't exist")
                return

            if not self.server.database.is_group_member(group_name, context["from_user"]):
                self.bad_request_error(connection, "You're not in this group")
                return

            # Send to all members except sender
            members = self.server.database.get_group_members(group_name)
            for row in members:
                member = row["username"]
                if member == context["from_user"]:
                    continue

                member_conn = self.get_user_connection(member)
                group_context = context.copy()
                group_context.update({
                    "target_conn": member_conn,
                    "recipient": member,
                    "group_name": group_name
                })

                self.route_message(message_name, group_context)
                
    def route_message(self, message_name, context):
        if message_name.startswith("MEDIA_"):
            self.handle_media_message(message_name, context)
        else:
            self.handle_text_message(message_name, context)

    def handle_media_message(self, message_name, ctx):

        target_conn = ctx["target_conn"]

        if message_name == "MEDIA_OFFER":
            # Store it regardless on online status
            self.media_queue.add_offer(
                transfer_id=ctx["transfer_id"],
                sender=ctx["from_user"],
                sender_port=ctx["sender_port"],
                recipient=ctx["chat_id"])
        
        if message_name == "MEDIA_OFFER":

            print(f"handle_MSG: from={ctx['from_user']}, chat_id={ctx['chat_id']}, chat_type={ctx['chat_type']}, target_conn={target_conn}")

            self.forward_MEDIA_OFFER(
                target_conn,
                ctx["from_user"],
                ctx["chat_id"],
                ctx["chat_type"],
                ctx["transfer_id"],
                ctx["filename"],
                ctx["filesize"],
                ctx["sender_port"]
            )

        elif target_conn and message_name == "MEDIA_RESPONSE":
            pass

    def add_offer(self, transfer_id, sender, sender_port, recipient):
            """Store an offer"""
            with self.lock:
                self.pending_offers[transfer_id] = {
                    'sender': sender,
                    'sender_port': sender_port,
                    'recipient': recipient,
                    'timestamp': time.time()
                }
            print(f"Added offer {transfer_id}")

    def get_and_remove(self, transfer_id):
        """Get an offer and remove it (atomic)"""
        with self.lock:
            return self.pending_offers.pop(transfer_id, None)


    def handle_text_message(self, message_name, ctx):

        target_conn = ctx["target_conn"]

        if target_conn and message_name == "MSG":
            print(f"handle_MSG: from={ctx['from_user']}, chat_id={ctx['chat_id']}, chat_type={ctx['chat_type']}, target_conn={target_conn}")

            self.forward_message(
                target_conn,
                ctx["from_user"],
                ctx["chat_id"],
                ctx["chat_type"],
                ctx["msg_id"],
                ctx["timestamp"],
                ctx["payload"]
            )

        else:
            self.server.database.store_offline_message(
                ctx["msg_id"],
                ctx["from_user"],
                ctx["recipient"],
                ctx["chat_type"],
                ctx["group_name"],
                ctx["payload"],
                ctx["timestamp"]
            ) 


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

    def forward_MEDIA_OFFER(self, recipient_conn, from_user, chat_id, chat_type, transfer_id, filename, filesize, sender_port):
            recipient_conn.sendJson({
                "message_name": "MEDIA_OFFER",
                "data": {
                "from": from_user,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "transfer_id": transfer_id,
                "filename": filename,
                "filesize": filesize,
                "sender_port": sender_port
                }
            })
    
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
