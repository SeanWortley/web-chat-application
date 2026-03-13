import socket
import threading
import struct
import os
import time

class UDPConnection:
    def __init__(self, client):
        self.client = client
        self.socket = None
        self.running = False

    def start(self):
        """Start UDP listener on a random port."""
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

        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)
                self.client.handle_packet(data, addr)

            except Exception as e:
                if self.running:
                    print(f"[UDP] Listen error: {e}")

    def stop(self):
        """Stop listener and close socket."""
        self.running = False
        if self.socket:
            self.socket.close()
        #print("[UDP] Stopped")

    def retransmit(self, transfer_id, chunk_index, peer_ip, peer_port):
        """Request retransmission of a specific chunk."""
        packet = struct.pack("!BIIB", self.NACK, transfer_id, chunk_index, 0)
        self.socket.sendto(packet, (peer_ip, peer_port))

    def send(self, data, address):
        self.socket.sendto(data, address)

    def receive(self, buffer_size=1024):
        return self.socket.recvfrom(buffer_size)