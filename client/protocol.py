from hashlib import sha256
import time
from tokenize import group
import json
from pathlib import Path

class Protocol:
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
            "MEDIA_OFFER": self.handle_incoming_media_offer
        }

    def handleIncoming(self, connection, serverMessage):
        #print(f"handleIncoming: {serverMessage}")
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
        self.client.username = message.get("from")

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
        self.client.username = message.get("from")
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
        msg_id = f"msg_{int(time.time())}"
        timestamp = time.time()
        
        connection.sendJson({
            "message_name": "MSG",
            "data": {
                "type": "DATA",
                "from": self.client.username,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "msg_id": msg_id,
                "timestamp": timestamp,
                "payload": text
            }
            
        })

    def media_offer(self, connection, chat_id, filepath, chat_type, sender_port):

        # Validate path
        file_path = Path(filepath)
        if not file_path.exists() and not file_path.isfile(filepath):
            print(f"File not found: {filepath}")
            return
    
        filename = file_path.name
        filesize = file_path.stat().st_size
        transfer_id = f"msg_{int(time.time())}"

        connection.sendJson({
            "message_name": "MEDIA_OFFER",
            "data": {
                "from": self.client.username,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "transfer_id": transfer_id,
                "filename": filename,
                "filesize": filesize,
                "sender_port": sender_port

            } 
        })


    def handle_incoming_media_offer(self, connection, message):
        data = message.get("data", {})
        self.client.interface.display(f"{data.get("chat_id")} wants to send you {data.get("filename")}!")
        answer = self.client.interface.accept_or_reject_offer()

        if answer.lower() == "accept":
            self.accepted_media_response(connection, message)
        else:
            self.rejected_media_response(connection, message)

    def accepted_media_response():
        pass

    def rejected_media_response(self, message):
        data = message.get("data", {})
        
        
    
    def media_response(self, connection, chat_id, chat_type, status, transfer_id, receiver_port):
        connection.sendJson({
            "message_name": "MEDIA_RESPONSE",
            "data": {
                "from": self.client.username,
                "chat_id": chat_id,
                "chat_type": chat_type,
                "status": status,
                "transfer_id": transfer_id,
                "receiver_port": receiver_port

            } 
        })
        pass
    
    def handle_MSG(self, connection, message):
    #Display incoming message
        #print("Ekse, you have a new message coming through")

        data = message["data"]
        from_user = data.get("from")
        chat_id = data.get("chat_id")
        chat_type = data.get("chat_type")
        payload = data.get("payload")

        #print(f"handle_MSG: from={from_user}, chat_id={chat_id}, chat_type={chat_type}, current_chat={self.client.interface.current_chat}")


        if chat_type == "private":
            channel = from_user
        elif chat_type == "group":
            channel = chat_id
        else:
            print("Unknown chat type:", chat_type)

        #print(f"channel={channel}, current_chat={self.client.interface.current_chat}")
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
        self.client.interface.process_unsent_batch(groups)


    def handle_MSG_DELIVERED(self, connection, message):
    #Show message delivery confirmation
        data = message["data"]
        msg_id = data.get("message_id")
        recipients = data.get("recipients", [])
        self.client.interface.display(f"✓ Message delivered to: {', '.join(recipients)}")
