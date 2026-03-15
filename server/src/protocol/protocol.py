import threading
import time


class Protocol:
    """
    Handles the messaging protocol used by the server.

    The Protocol class is responsible for interpreting incoming client
    commands and dispatching them to the appropriate handler methods.
    Each supported command is mapped to a handler function through the
    `handlers` dictionary.

    It also manages pending media offers and provides thread-safe
    access using a lock when modifying shared state.
    """
    def __init__(self, server):
        """
        Initializes the protocol handler.

        Args:
            server (Server): Reference to the main server instance that
                owns this protocol handler. Used to access server state,
                connections, and shared resources.

        Attributes:
            server (Server): The parent server instance.
            pending_offers (dict): Stores pending media offers between users.
            lock (threading.Lock): Ensures thread-safe access to shared data.
            handlers (dict): Maps protocol command strings to their
                corresponding handler methods.
        """
        self.server = server
        self.pending_offers = {}
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
            "MEDIA_OFFER": self.handle_MSG,
            "MEDIA_RESPONSE": self.handle_MSG
        }

    def handleIncoming(self, connection, clientMessage):
        """
        Processes an incoming message from a client and dispatches it to the
        appropriate protocol handler.

        This method extracts the message type from the incoming message and
        looks up the corresponding handler function in the `handlers` mapping.
        If a matching handler is found, it is executed with the connection and
        message data. If no handler exists for the message type, the event is
        logged as an unknown message.

        Args:
            connection (Connection): The client connection that sent the message.
            clientMessage (dict): The parsed message received from the client.
                It must contain a `"message_name"` field specifying the command.

        Raises:
            KeyError: If `"message_name"` is missing from the message dictionary.
        """
        messageName = clientMessage["message_name"]
        handler = self.handlers.get(messageName)
        if handler:
            handler(connection, clientMessage)
        else:
            self.server.log(f"Unknown message: {clientMessage['message_name']}")

    def handle_AUTH(self, connection, message):
        """
        Handles client authentication.

        Verifies the provided username and hashed password against the
        database. If valid and the user is not already logged in, the
        connection is authenticated.

        Args:
            connection (Connection): The client connection attempting login.
            message (dict): The AUTH message containing login credentials.
        """
        username = message["data"]["username"]
        hashed_pword = message["data"]["hashed_password"]

        user = self.server.database.get_user(username)
        if username in self.server.active_users:
            self.AUTH_FAIL(connection, "This user is already logged in!")
        elif user and hashed_pword == user["hashed_password"]:
            connection.authenticated = True
            connection.loggedInAs = username
            self.server.active_users.append(username)
            self.AUTH_OK(connection)
        else:
            self.AUTH_FAIL(connection, "Incorrect name or password!")

    def handle_CREATE_ACCOUNT(self, connection, message):
        """
        Handles creation of a new user account.

        If the username does not exist, creates the account, authenticates
        the connection, and sends a success message. Otherwise, sends a failure.

        Args:
            connection (Connection): The client connection requesting account creation.
            message (dict): The CREATE_ACCOUNT message containing credentials.
        """
        username = message["data"]["username"]
        hashed_pword = message["data"]["hashed_password"]

        user = self.server.database.get_user(username)
        if not user:
            self.server.database.create_user(username, hashed_pword)
            connection.authenticated = True
            connection.loggedInAs = username
            self.CREATE_ACCOUNT_OK(connection)
        else:
            self.CREATE_ACCOUNT_FAIL(connection)

    def handle_LOGOUT(self, connection, message):
        """
        Logs out a user and updates server state.

        Marks the connection as unauthenticated, removes the user from active
        users, and sends a logout acknowledgement.

        Args:
            connection (Connection): The client connection requesting logout.
            message (dict): The LOGOUT message (unused, but included for consistency).
        """
        username = connection.loggedInAs
        connection.authenticated = False
        connection.loggedInAs = None
        if username in self.server.active_users:
            self.server.active_users.remove(username)
        self.LOGOUT_ACK(connection, username)

    def handle_REQUEST_UNSENT_MESSAGES(self, connection, message):
        """
        Sends offline messages to the authenticated user.

        Groups messages by sender or group and sends them to the client,
        then deletes them from the database.

        Args:
            connection (Connection): The authenticated client connection.
            message (dict): The request message (unused here).
        """
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
        """
        Sends unsent messages grouped by sender or group to the client.

        Args:
            connection (Connection): The client connection to send messages to.
            groups (dict): Dictionary of grouped offline messages.
        """
        connection.sendJson({
            "message_name": "UNSENT_MESSAGES",
            "data": {
                "groups": groups
            }
        })

    def AUTH_OK(self, connection):
        """
        Sends an authentication success message to the client.

        Args:
            connection (Connection): The authenticated client connection.
        """
        welcome_message = f"Welcome back, {connection.loggedInAs}!"

        connection.sendJson({
            "message_name": "AUTH_OK",
            "from": connection.loggedInAs,
            "data": {
                "welcome_message": welcome_message}
        })

    def AUTH_FAIL(self, connection, error_message):
        """
        Sends an authentication failure message to the client.

        Args:
            connection (Connection): The client connection that failed authentication.
            error_message (str): Explanation of the failure.
        """
        connection.sendJson({
            "message_name": "AUTH_FAIL",
            "data": {
                "error_code": error_message}
        })

    def CREATE_ACCOUNT_OK(self, connection):
        """
        Sends account creation success message to the client.

        Args:
            connection (Connection): The client connection that successfully created an account.
        """
        welcome_message = f"welcome new user, {connection.loggedInAs}!"

        connection.sendJson({
            "message_name": "CREATE_ACCOUNT_OK",
            "from": connection.loggedInAs,
            "data": {
                "welcome_message": welcome_message}
        })

    def CREATE_ACCOUNT_FAIL(self, connection):
        """
        Sends account creation failure message if username already exists.

        Args:
            connection (Connection): The client connection that attempted account creation.
        """
        error_message = "A user with that name already exists!"

        connection.sendJson({
            "message_name": "CREATE_ACCOUNT_FAIL",
            "data": {
                "error_message": error_message
            }
        })

    def LOGOUT_ACK(self, connection, username):
        """
        Sends a logout acknowledgement message to the client.

        Args:
            connection (Connection): The client connection logging out.
            username (str | None): Username of the client or None if already logged out.
        """
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
        Processes an incoming message (private or group) and routes it.

        Checks authentication and validates recipients or groups, then
        forwards the message or stores it offline if the recipient is unavailable.

        Args:
            connection (Connection): The client sending the message.
            message (dict): The message payload containing metadata and content.
        """
        message_name = message.get("message_name")
        data = message.get("data", {})
        raw_chat_id = data.get("chat_id")
        chat_id = raw_chat_id.strip() if isinstance(raw_chat_id, str) else raw_chat_id
        from_user = connection.loggedInAs

        context = {
            "source_conn": connection,
            "from_user": from_user,
            "chat_id": chat_id,
            "chat_type": data.get("chat_type"),
            "msg_id": data.get("msg_id", "unknown"),
            "timestamp": time.time(),
            "payload": data.get("payload", ""),
            "transfer_id": data.get("transfer_id"),
            "filename": data.get("filename"),
            "filesize": data.get("filesize"),
            "sender_port": data.get("sender_port"),
            "status": data.get("status"),
            "receiver_port": data.get("receiver_port")
        }

        if not connection.authenticated:
            self.MSG_NAK(connection, context.get("chat_id"), "User isn't authenticated")
            return

        if context["chat_type"] == "private":
            recipient = context["chat_id"]
            if recipient == context.get("from_user"):
                self.MSG_NAK(connection, context["chat_id"], "You can't send a message to yourself")
                return
            if not self.server.database.get_user(context["chat_id"]):
                self.MSG_NAK(connection, context.get("chat_id"), "Recipient doesn't exist")
                return
            recipient_conn = self.get_user_connection(recipient)

            context.update({
                "target_conn": recipient_conn,
                "recipient": recipient,
                "group_name": None
            })

            self.route_message(message_name, context)

        elif context["chat_type"] == "group":
            group_name = context["chat_id"]

            if not self.server.database.get_group(group_name):
                self.MSG_NAK(connection, context.get("chat_id"), "Group doesn't exist")
                return

            if not self.server.database.is_group_member(group_name, context["from_user"]):
                self.MSG_NAK(connection, context.get("chat_id"), "You're not in this group")
                return

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
        """
        Routes a message to either media or text handler based on its type.

        Args:
            message_name (str): The type of message (e.g., "MSG", "MEDIA_OFFER").
            context (dict): Context dictionary with message details.
        """
        if message_name.startswith("MEDIA_"):
            self.handle_media_message(message_name, context)
        else:
            self.handle_text_message(message_name, context)

    def handle_media_message(self, message_name, ctx):
        """
        Handles media messages like MEDIA_OFFER or MEDIA_RESPONSE.

        Updates pending offers, forwards offers to recipients, and notifies
        senders of responses.

        Args:
            message_name (str): Type of media message.
            ctx (dict): Message context including sender, recipient, and metadata.
        """
        target_conn = ctx["target_conn"]

        if message_name == "MEDIA_OFFER":
            if ctx["chat_type"] == "private" and not target_conn:
                self.MSG_NAK(
                    ctx["source_conn"],
                    ctx["chat_id"],
                    "Recipient is offline"
                )
                return

            self.add_offer(
                transfer_id=ctx["transfer_id"],
                sender=ctx["from_user"],
                sender_port=ctx["sender_port"],
                recipient=ctx["chat_id"]
            )

            if target_conn:
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

        elif message_name == "MEDIA_RESPONSE":
            transfer_id = ctx.get("transfer_id")
            with self.lock:
                offer = self.pending_offers.get(transfer_id)
                if offer:
                    responder = ctx["from_user"]
                    if responder not in offer['responders']:
                        offer['responders'].add(responder)
                        sender_conn = self.get_user_connection(offer['sender'])
                        if sender_conn:
                            self.forward_MEDIA_RESPONSE(
                                sender_conn,
                                offer['sender'],
                                responder,
                                ctx["status"],
                                transfer_id,
                                ctx.get("receiver_port")
                            )
                else:
                    print(f"No offer found for transfer_id {transfer_id}")

    def add_offer(self, transfer_id, sender, sender_port, recipient):
        """
        Records a new media transfer offer in the pending offers dictionary.

        Args:
            transfer_id (str): Unique ID of the media transfer.
            sender (str): Username of the sender.
            sender_port (int): Port used by the sender.
            recipient (str): Username of the recipient.
        """
        with self.lock:
            self.pending_offers[transfer_id] = {
                'sender': sender,
                'sender_port': sender_port,
                'recipient': recipient,
                'responders': set(),
                'timestamp': time.time()
            }
        print(f"Added offer {transfer_id}")

    def handle_text_message(self, message_name, ctx):
        """
        Sends text messages to online recipients or stores them offline.

        Args:
            message_name (str): The type of message (e.g., "MSG").
            ctx (dict): Message context including sender, recipient, and payload.
        """
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
        """
        Handles creation of a new group chat.

        Validates authentication, ensures the group doesn't exist, then
        creates it and sends acknowledgement.

        Args:
            connection (Connection): The client requesting group creation.
            message (dict): Contains the group name.
        """
        if not connection.authenticated:
            self.CREATE_GROUP_ACK(connection, "fail", "You aren't logged in")
            return

        group_name = message["data"]["group_name"]
        username = connection.loggedInAs

        if self.server.database.get_group(group_name):
            self.CREATE_GROUP_ACK(connection, "fail", "Group already exists")
            return

        self.server.database.create_group(group_name, username)
        self.CREATE_GROUP_ACK(connection, "success", f"Group '{group_name}' created!")

    def handle_JOIN_GROUP(self, connection, message):
        """
        Adds an authenticated user to an existing group.

        Validates authentication, checks group existence and membership,
        then adds the user and sends acknowledgement.

        Args:
            connection (Connection): The client joining the group.
            message (dict): Contains the group name.
        """
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
        self.JOIN_GROUP_ACK(connection, "success", f"You joined '{group_name}'")

    def handle_GROUP_LIST(self, connection, message):
        """
        Sends a list of groups the authenticated user belongs to.

        Args:
            connection (Connection): The client requesting the group list.
            message (dict): Unused placeholder for consistency.
        """
        if not connection.authenticated:
            self.GROUP_LIST_ACK(connection, "fail", [], "You aren't logged in")
            return

        username = connection.loggedInAs
        groups = self.server.database.get_user_groups(username)
        group_names = [row["group_name"] for row in groups]

        self.GROUP_LIST_ACK(connection, "success", group_names, None)

    def GROUP_LIST_ACK(self, connection, result, groups, message):
        """
        Sends acknowledgement for a group list request.

        Args:
            connection (Connection): The client receiving the list.
            result (str): "success" or "fail".
            groups (list): List of group names.
            message (str | None): Optional status message.
        """
        connection.sendJson({
            "message_name": "GROUP_LIST_ACK",
            "data": {
                "result": result,
                "groups": groups,
                "message": message
            }
        })

    def CREATE_GROUP_ACK(self, connection, result, message):
        """
        Sends acknowledgement for a create group request.

        Args:
            connection (Connection): The client receiving the acknowledgement.
            result (str): "success" or "fail".
            message (str): Status message to send.
        """
        connection.sendJson({
            "message_name": "CREATE_GROUP_ACK",
            "data": {
                "result": result,
                "message": message
            }
        })

    def JOIN_GROUP_ACK(self, connection, result, message):
        """
        Sends acknowledgement for a join group request.

        Args:
            connection (Connection): The client receiving the acknowledgement.
            result (str): "success" or "fail".
            message (str): Status message to send.
        """
        connection.sendJson({
            "message_name": "JOIN_GROUP_ACK",
            "data": {
                "result": result,
                "message": message
            }
        })

    def get_user_connection(self, username):
        """
        Returns the active connection object for a given authenticated user.

        Args:
            username (str): The username to look up.

        Returns:
            Connection | None: The active connection or None if not found.
        """
        for conn in self.server.connections:
            if conn.loggedInAs == username and conn.authenticated:
                return conn
        return None

    def forward_MEDIA_OFFER(self, recipient_conn, from_user, chat_id, chat_type, transfer_id, filename, filesize, sender_port):
        """
        Forwards a media offer to the intended recipient.

        Args:
            recipient_conn (Connection): Recipient's connection object.
            from_user (str): Sender's username.
            chat_id (str): Target chat or group ID.
            chat_type (str): "private" or "group".
            transfer_id (str): Unique media transfer ID.
            filename (str): Name of the file being transferred.
            filesize (int): Size of the file in bytes.
            sender_port (int): Port used by the sender.
        """
        media_offer_sender_conn = self.get_user_connection(from_user)
        if not media_offer_sender_conn:
            self.server.log(f"MEDIA_OFFER skipped: sender connection not found for '{from_user}'")
            return
        md_offer_sender_ip = media_offer_sender_conn.socket.getpeername()[0]

        routed_chat_id = from_user if chat_type == "private" else chat_id

        recipient_conn.sendJson({
            "message_name": "MEDIA_OFFER",
            "data": {
                "from": from_user,
                "chat_id": routed_chat_id,
                "chat_type": chat_type,
                "transfer_id": transfer_id,
                "filename": filename,
                "filesize": filesize,
                "sender_port": sender_port,
                "sender_ip": md_offer_sender_ip
            }
        })

    def forward_MEDIA_RESPONSE(self, recipient_conn, to_user, from_user, status, transfer_id, receiver_port):
        """
        Forwards a media response (accept/decline) to the original sender.

        Args:
            recipient_conn (Connection): Original sender's connection object.
            to_user (str): Intended recipient username.
            from_user (str): Responder's username.
            status (str): Status of the media transfer.
            transfer_id (str): Unique media transfer ID.
            receiver_port (int): Port on which recipient can receive data.
        """
        media_response_sender_conn = self.get_user_connection(from_user)
        if not media_response_sender_conn:
            self.server.log(f"MEDIA_RESPONSE skipped: sender connection not found for '{from_user}'")
            return
        md_response_sender_ip = media_response_sender_conn.socket.getpeername()[0]
        recipient_conn.sendJson({
            "message_name": "MEDIA_RESPONSE",
            "data": {
                "from": from_user,
                "to": to_user,
                "status": status,
                "transfer_id": transfer_id,
                "receiver_port": receiver_port,
                "receiver_ip": md_response_sender_ip
            }
        })

    def forward_message(self, recipient_conn, from_user, chat_id, chat_type, msg_id, timestamp, payload):
        """
        Sends a text message to a recipient connection.

        Args:
            recipient_conn (Connection): Recipient's connection object.
            from_user (str): Sender's username.
            chat_id (str): Chat or group ID.
            chat_type (str): "private" or "group".
            msg_id (str): Unique message ID.
            timestamp (float): Time the message was sent.
            payload (str): Message content.
        """
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

    def MSG_NAK(self, connection, chat_id, error_message):
        """
        Sends a negative acknowledgement (NAK) for a message.

        Args:
            connection (Connection): The client to notify.
            chat_id (str): ID of the intended chat.
            error_message (str): Reason the message could not be delivered.
        """
        connection.sendJson({
            "message_name": "MSG_NAK",
            "data": {
                "chat_id": chat_id,
                "error_message": error_message
            }
        })

    def SHUTDOWN(self, connection):
        """
        Sends a shutdown notification to a client connection.

        Args:
            connection (Connection): The client being notified of server shutdown.
        """
        connection.sendJson({
            "message_name": "SHUTDOWN"
        })
