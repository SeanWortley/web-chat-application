Functionality to do:

Server side database
client side database
Handle mutliple chats
user account creation

Messages to do:

AUTH
COMMAND
username, hashed_password
Client requests authentication with the server.

AUTH_OK
CONTROL
welcome_message
Server confirms successful login.

AUTH_FAIL
CONTROL
error_code
Server reports authentication fail

LOGOUT
COMMAND
(none)
Client notifies the server it will end the request.

LOGOUT_ACK
CONTROL
goodbye_message
Server confirms logout.

CREATE_GROUP
COMMAND
group_name
Client requests a new group.

CREATE_GROUP_ACK
CONTROL
result, error_code
Server confirms or rejects creation of this group.

JOIN_GROUP
COMMAND
group_name
Client requests to join a group.

JOIN_GROUP_ACK
CONTROL
result, error_code
Server confirms or rejects the admission to this group.

LEAVE_GROUP
COMMAND
group_name
Client requests to leave a group.

LEAVE_GROUP_ACK
CONTROL
result, error code
Server confirms or rejects this leave request.

GROUP_LIST
COMMAND
(none)
Client requests a list of all groups the user belongs to.

GROUP_LIST_RESPONSE
CONTROL
[groups]
Server returns list of groups the user is in.

GROUP_MEMBERS
COMMAND
group_name
Client requests a list of members in a group.

GROUP_MEMBERS_RESPONSE
CONTROL
[members]
Server returns list of group members.

MSG
DATA
from, chat_id, chat_type, msg_id, timestamp
Message to a chat (either a single user, or a group of users), via the server. “chat_id” is either a username or a group name, chat_type is private or group. The message text will reside in the payload.

MSG_DELIVERED
CONTROL
message_id, [recipients]
Server notifies the sender that the message was received by the recipient(s).

MSG_STORED
CONTROL
message_id [recipients]
Server notifies the sender that the message was stored for later receival by offline recipient(s).

MEDIA_OFFER
COMMAND
from, chat_id, file_name, file_size, media_id
Client (sender) notifies the server it wishes to share media with user(s).

SETUP_P2P
CONTROL
from, to, file_name, file_size, media_id, sender_ip, sender_port
The server tells the recipient client(s) that a media file is on offer, and instructs them how to connect via UDP to the sender and receive them.

MEDIA_ACCEPT
COMMAND
from, to, media_id, receiver_ip, receiver_port
The recipient notifies the sender to begin the media transfer.

PACKET
DATA
media_id, packet_id, total_packets, packet_size
The payload is a portion of the raw binary media file.

MEDIA_DONE
CONTROL
media_id, total_packets, file_size
The sender indicates that all media packets have been sent.

MEDIA_ACK
COMMAND
media_id
The recipient confirms that all data has been received.

BAD_REQUEST_RESPONSE
CONTROL
error_code, error_message, offending_message
Server informs the client of an invalid message.

OFFLINE_ERROR_RESPONSE
CONTROL
error_code, error_message, recipient
Server informs the sender that they attempted to share a media file with an offline person.

UNSUPPORTED_FILETYPE_RESPONSE
CONTROL
error_code, error_message, file_type
Server informs the sender that they attempted to share an unsupported media file.

Run from project root

Server:
python3 server/main.py --host 127.0.0.1 --port 12000

Server clean runtime DB only:
python3 server/main.py --clean

Client (GUI):
python3 client/main.py --host 127.0.0.1 --port 12000

Client (Terminal):
python3 client/main.py --host 127.0.0.1 --port 12000 --terminal

Client clean runtime DB only:
python3 client/main.py --clean
