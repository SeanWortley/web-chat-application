import socket
import threading
import struct

class UDPConnection:
    """Manages UDP socket lifecycle for peer-to-peer transfers."""

    def __init__(self, client):
        """
        Initializes a UDP connection for P2P transfers.

        Args:
            client (Client): Reference to the parent client or protocol handler.
        """
        self.client = client
        self.socket = None
        self.running = False

    def start(self):
        """
        Starts the UDP listener on a dynamically assigned port and spawns a listener thread.

        Returns:
            int: The assigned UDP port number.
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', 0))  # OS assigns port
        self.port = self.socket.getsockname()[1]
        self.running = True
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()
        #print(f"[UDP] Listening on port {self.port}")
        return self.port
    
    def _listen(self):
        """
        Continuously listens for incoming UDP packets and forwards them to the client's handler.
        """
        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                self.client.handle_packet(data, addr)

            except Exception as e:
                if self.running:
                    print(f"[UDP] Listen error: {e}")

    def stop(self):
        """
        Stops the listener and closes the UDP socket.
        """
        self.running = False
        if self.socket:
            self.socket.close()
        #print("[UDP] Stopped")

    def send(self, data, address):
        """
        Sends raw data to a specific UDP address.

        Args:
            data (bytes): Packet data to send.
            address (tuple): (IP, port) tuple of the recipient.
        """
        self.socket.sendto(data, address)