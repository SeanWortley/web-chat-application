from hashlib import sha256
import time
from tokenize import group
import uuid
import json
from pathlib import Path

class CSProtocol:
    def __init__(self, client):
        self.client = client
        self.handlers = {
            "AUTH_OK": self.handle_AUTH_OK,
            "AUTH_FAIL": self.handle_AUTH_FAIL,
            "CREATE_ACCOUNT_OK": self.handle_CREATE_ACCOUNT_OK,
            "CREATE_ACCOUNT_FAIL": self.handle_CREATE_ACCOUNT_FAIL,
            "CREATE_GROUP_ACK": self.handle_CREATE_GROUP_ACK,
            "GROUP_LIST_ACK": self.handle_GROUP_LIST_ACK,
            "JOIN_GROUP_ACK": self.handle_JOIN_GROUP_ACK,
            "LOGOUT_ACK": self.handle_LOGOUT_ACK,
            "MSG": self.handle_MSG,  
            "MSG_DELIVERED": self.handle_MSG_DELIVERED,
            "UNSENT_MESSAGES": self.handle_UNSENT_MESSAGES,
            "MEDIA_OFFER": self.handle_incoming_media_offer,
            "MEDIA_RESPONSE": self.handle_incoming_media_response,
            "MSG_NAK": self.handle_MSG_NAK,
            "SHUTDOWN": self.handle_SHUTDOWN,
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
        self.client.interface.logged_in = True
        self.client.authenticated = True
        self.client.loggedInAs = message.get("from")
        self.client.interface.loggedInAs = message.get("from")
        self.client.assign_db()

        self.client.interface.display(message["data"]["welcome_message"])
        self.REQUEST_UNSENT_MESSAGES(connection)
        self.client.interface.show_logged_in_menu()
        self.client.interface.resume()
    
    def handle_AUTH_FAIL(self, connection, message):
        self.client.interface.display(f"Failed to authenticate: {message["data"]["error_code"]}")
        self.client.interface.show_logged_out_menu()
        self.client.interface.resume()

    def handle_CREATE_ACCOUNT_OK(self, connection, message):
        self.client.interface.display(message["data"]["welcome_message"])
        self.client.interface.logged_in = True
        self.client.loggedInAs = message.get("from")
        self.client.interface.loggedInAs = message.get("from")
        self.client.assign_db()
        self.client.interface.show_logged_in_menu()
        self.client.interface.resume()

        
        

    def handle_CREATE_ACCOUNT_FAIL(self, connection, message):
        self.client.interface.display(message["data"]["error_message"])
        self.client.interface.show_logged_out_menu()
        self.client.interface.resume()

    def handle_LOGOUT_ACK(self, connection, message):
        self.client.interface.display(message["data"]["goodbye_message"])
        self.client.authenticated = False
        self.client.loggedInAs = None
        self.client.unassign_db()
        self.client.interface.loggedInAs = None
        self.client.interface.show_logged_out_menu()
        self.client.interface.resume()

    def handle_CREATE_GROUP_ACK(self, connection, message):
        result =  message["data"]["result"]
        if result == "success":
            self.client.interface.display(f'Group creation successful!\n{message["data"]["message"]}')
        else:
            self.client.interface.display(f'Group creation unsuccessful!\n{message["data"]["message"]}')
        self.client.interface.resume()

    def handle_JOIN_GROUP_ACK(self, connection, message):
        result = message["data"]["result"]
        if result == "success":
            self.client.interface.display(f'Successfully joined this group!\n{message["data"]["message"]}')
        else:
            self.client.interface.display(f'You weren\'t able to join this group!\n{message["data"]["message"]}')
        self.client.interface.resume()

    def handle_GROUP_LIST_ACK(self, connection, message):
        result = message["data"]["result"]
        if result == "fail":
            self.client.interface.display(message["data"]["message"])
        else:
            groups = message["data"]["groups"]
            if groups:
                for i in groups:
                    self.client.interface.display(i)
            else:
                self.client.interface.display("You do not belong to any groups")
        self.client.interface.resume()

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

    def LOGOUT(self, connection):
        connection.sendJson({
            "message_name": "LOGOUT"
        })

    def CREATE_GROUP(self, connection, group_name):
        connection.sendJson({
            "message_name": "CREATE_GROUP",
            "data":
            {
                "group_name": group_name
            }
        })        

    def JOIN_GROUP(self, connection, group_name):
        connection.sendJson({
            "message_name": "JOIN_GROUP",
            "data":
            {
                "group_name": group_name
            }
        })
    
    def GROUP_LIST(self, connection):
        connection.sendJson({
            "message_name": "GROUP_LIST"
        })


    def LEAVE_GROUP(self, connection, group_name):
        connection.sendJson({
            "message_name": "LEAVE_GROUP",
            "data":
            {
                "group_name": group_name
            }
        })

    def MSG(self, connection, chat_id, chat_type, text):
        msg_id = str(uuid.uuid4())
        timestamp = time.time()
        
        outgoing = {
            "message_name": "MSG",
            "data": {
                "type": "DATA",
                "from": self.client.loggedInAs,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "msg_id": msg_id,
                "timestamp": timestamp,
                "payload": text
            }
        }

        if chat_type == "private":
            self.client.database.store_private_message(outgoing, False)
        
        if chat_type == "group":
            self.client.database.store_group_message(outgoing, False)
        connection.sendJson(outgoing)

        
    def MEDIA_OFFER(self, connection, chat_id, transfer_id, filepath, chat_type, sender_port):

    
        file_path = Path(filepath)
        filename = file_path.name
        filesize = file_path.stat().st_size

        connection.sendJson({
            "message_name": "MEDIA_OFFER",
            "data": {
                "from": self.client.loggedInAs,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "filename": filename,
                "filesize": filesize,
                "sender_port": sender_port,
                "transfer_id": transfer_id
            } 
        })

    def handle_incoming_media_offer(self, connection, message):
        self.client.interface.handle_incoming_offer(message)
    
    def MEDIA_RESPONSE(self, connection, chat_id, chat_type, status, transfer_id, receiver_port):
        connection.sendJson({
        "message_name": "MEDIA_RESPONSE",
        "data": {
            "from": self.client.loggedInAs,
            "chat_id": chat_id,
            "chat_type": chat_type,
            "status": status,
            "transfer_id": transfer_id,
            "receiver_port": receiver_port
        }
    })
    
    def handle_incoming_media_response(self, connection, message):
        self.client.interface.handle_incoming_response(message)
    
    def handle_MSG(self, connection, message):
        #print("Ekse, you have a new message coming through")
        data = message.get("data", {})
        from_user = data.get("from")
        chat_id = data.get("chat_id")
        chat_type = data.get("chat_type")

        if from_user == self.client.loggedInAs:
            return

        if chat_type == "private":
            channel = from_user
            self.client.database.store_private_message(message)
        elif chat_type == "group":
            channel = chat_id
            self.client.database.store_group_message(message)
        else:
            print("Unknown chat type:", chat_type)
            return
            
        self.client.interface.process_msg(message, channel)

        """
        if chat_type == "private":
            self.client.interface.display(f"\n[PM from {from_user}]: {payload}")
        elif chat_type == "group":
            self.client.interface.display(f"\n[{chat_id}] {from_user}: {payload}")
        """

    def REQUEST_UNSENT_MESSAGES(self, connection):
        connection.sendJson({
            "message_name": "REQUEST_UNSENT_MESSAGES",
        })
    
    def handle_UNSENT_MESSAGES(self, connection, message):
        groups = message["data"]["groups"]
        
        for chat_id, messages in groups.items():
            for msg in messages:
                if msg["chat_type"] == "private":
                    self.client.database.store_private_message({
                        "data": {
                            "from": msg["sender"],
                            "chat_id": chat_id,
                            "chat_type": "private",
                            "msg_id": msg["msg_id"],
                            "payload": msg["content"],
                            "timestamp": msg["timestamp"]
                        }
                    })
                elif msg["chat_type"] == "group":
                    self.client.database.store_group_message({
                        "data": {
                            "from": msg["sender"],
                            "chat_id": chat_id,
                            "chat_type": "group",
                            "msg_id": msg["msg_id"],
                            "payload": msg["content"],
                            "timestamp": msg["timestamp"]
                        }
                    })
        
        self.client.interface.process_unsent_batch(groups)


    def handle_MSG_DELIVERED(self, connection, message):
    #Show message delivery confirmation
        data = message["data"]
        msg_id = data.get("message_id")
        recipients = data.get("recipients", [])
        self.client.interface.display(f"✓ Message delivered to: {', '.join(recipients)}")

    def handle_MSG_NAK(self, connection, message):
        data = message.get("data")
        chat_id = data.get("chat_id")
        error_message = data.get("error_message")


        match error_message:
            case "You can't send a message to yourself":
                self.client.interface.process_self_message()
                self.client.database.delete_private_chat_logs(chat_id)
            case "Recipient doesn't exist":
                self.client.interface.process_incorrect_recipient()
                self.client.database.delete_private_chat_logs(chat_id)
            case "Group doesn't exist":
                self.client.interface.process_incorrect_group()
                self.client.database.delete_group_chat_logs(chat_id)
            case "You're not in this group":
                self.client.interface.process_not_group_member()
                self.client.database.delete_group_chat_logs(chat_id)
    
    def handle_SHUTDOWN(self, connection, message):
        self.client.command_queue.put({
            "message_name": "shutdown"
        })