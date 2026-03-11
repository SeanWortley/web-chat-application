import socket
import threading
import os
import json
import time
import struct
from pathlib import Path

class UDPHandler:

    def __init__(self, client):

        self.client = client          # Reference to main client (for UI updates)
        self.callback = None      # Function to call on events (progress, complete, error)
        self.socket = None
        self.port = None
        self.running = False
        self.listener_thread = None

        # Transfer tracking
        self.sending = {}              # transfer_id -> sending info
        self.receiving = {}            # key (addr+transfer_id) -> receiving info

        # Constants
        self.CHUNK_SIZE = 8192
        self.TIMEOUT = 2.0
        self.MAX_RETRIES = 3

    def start(self):
        """Start UDP listener on a random port."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', 0))  # OS assigns port
        self.port = self.socket.getsockname()[1]
        self.running = True
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()
        print(f"[UDP] Listening on port {self.port}")
        return self.port

    def stop(self):
        """Stop listener and close socket."""
        self.running = False
        if self.socket:
            self.socket.close()
        print("[UDP] Stopped")

    def get_port(self):
        return self.port

    def initiate_udp_transfer(self, transfer_id, filepath, peer_ip, peer_port):
        """Start sending a file to a peer."""
        pass

    def get_udp_handler() :
        pass

    def get_port():
        pass