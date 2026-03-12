import socket
import threading
import os
import json
import time
import struct
from pathlib import Path

class UDPHandler:

    DATA = 0
    END = 1 
    ACK = 2 
    NACK = 3

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
        
        self.sent_packet = {}

        #receiver state
        self.recv_expected = {}
        self.recv_buffers = {} 
        self.recv_files = {}

        # Constants
        self.CHUNK_SIZE = 1024
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
    
    def _listen(self):

        while self.running:
            try:
                data, addr = self.socket.recvfrom(65535)

                packet_type = data[0]
                transfer_id = struct.unpack("!I", data[1:5])[0]

                if packet_type == self.DATA:
                    # Handle incoming file data
                    self.handle_data_packet(data, addr)

                elif packet_type == self.END:
                    # Handle end-of-file
                    self.handle_end_packet(addr, transfer_id)

                elif packet_type in (self.ACK, self.NACK):
                    # Handle sender feedback
                    peer_ip, peer_port = addr
                    self.handle_sender_feedback(data, peer_ip, peer_port)

            except Exception as e:
                if self.running:
                    print(f"[UDP] Listen error: {e}")

    def stop(self):
        """Stop listener and close socket."""
        self.running = False
        if self.socket:
            self.socket.close()
        print("[UDP] Stopped")

    def get_port(self):
        return self.port
    
    def retransmit(self, transfer_id, seq, peer_ip, peer_port):
        key = (transfer_id, seq)

        if key in self.sent_packet:
            packet = self.sent_packet[key]
            self.socket.sendto(packet, (peer_ip, peer_port))

    def initiate_udp_transfer(self, transfer_id, filepath, peer_ip, peer_port):
        """Start sending a file to a peer."""

        file_path = Path(filepath)

        if not file_path.exists():
            print(f"File not found: {filepath}")
            return

        seq = 0

        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(self.CHUNK_SIZE)

                if not chunk:
                    end_packet = struct.pack("!BII", 1, transfer_id, seq)
                    self.socket.sendto(end_packet, (peer_ip, peer_port))
                    break
                
                # How a packet is sent: [packet type][transfer_id][sequence number][chunk]
                packet = struct.pack("!BII", 0, transfer_id, seq) + chunk

                self.sent_packet[(transfer_id, seq)] = packet

                self.socket.sendto(packet, (peer_ip, peer_port))

                seq += 1
                time.sleep(0.001)

    def handle_sender_feedback(self, data, peer_ip, peer_port):

        packet_type, transfer_id, seq = struct.unpack("!BII", data[:9])

        if packet_type == 2:  # ACK
            key = (transfer_id, seq)
            if key in self.sent_packet:
                del self.sent_packet[key]

        elif packet_type == 3:  # NACK
            self.retransmit(transfer_id, seq, peer_ip, peer_port)

    def receiver_send_ack(self, addr, transfer_id, seq):
        packet = struct.pack("!BII", self.ACK, transfer_id, seq)
        self.socket.sendto(packet, addr)

    def receiver_send_nack(self, addr, transfer_id, seq):
        packet = struct.pack("!BII", self.NACK, transfer_id, seq)
        self.socket.sendto(packet, addr)

    def handle_data_packet(self, data, addr):
        if len(data) < 9:
            print(f"[UDP] Packet too short from {addr}, ignoring")
            return
        
        print("Received bytes:", data)
        print("Length:", len(data))
        
        packet_type, transfer_id, seq = struct.unpack("!BII", data[:9])
        chunk = data[9:]
        key = (addr, transfer_id)

        if key not in self.recv_expected:
            self.recv_expected[key] = 0
            self.recv_buffers[key] = {}
            self.recv_files[key] = open(f"recv_{transfer_id}.bin", "wb")

        expected = self.recv_expected[key]
        buffer = self.recv_buffers[key]
        file = self.recv_files[key]

        if seq == expected:
            file.write(chunk)
            self.recv_expected[key] += 1
            self.send_ack(addr, transfer_id, seq)

            while self.recv_expected[key] in buffer:
                file.write(buffer.pop(self.recv_expected[key]))
                self.recv_expected[key] += 1

        elif seq > expected:
            buffer[seq] = chunk
            self.send_nack(addr, transfer_id, expected)

        else:
            # Duplicate packet
            self.send_ack(addr, transfer_id, seq)


    def handle_end_packet(self, addr, transfer_id):
        key = (addr, transfer_id)

        if key in self.recv_files:
            self.recv_files[key].close()
            del self.recv_files[key]
            del self.recv_buffers[key]
            del self.recv_expected[key]
            print(f"[UDP] Transfer {transfer_id} complete")
                