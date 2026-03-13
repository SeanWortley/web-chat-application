import struct
import time
import threading
from pathlib import Path


class P2PProtocol:

    DATA = 0
    END = 1
    ACK = 2
    NACK = 3

    CHUNK_SIZE = 1024
    TIMEOUT = 2.0
    MAX_RETRIES = 3

    def __init__(self, client, udp_connection):

        self.client = client
        self.udp = udp_connection

        self.callback = None

        # Transfer tracking
        self.sending = {}
        self.receiving = {}

        self.sent_packet = {}

        # receiver state
        self.recv_expected = {}
        self.recv_buffers = {}
        self.recv_files = {}
        self.recv_filenames = {}

    def _temp_bin_path(self, transfer_id):
        incoming_dir = Path(__file__).resolve().parents[2] / "runtime" / "incoming"
        incoming_dir.mkdir(parents=True, exist_ok=True)
        username = self.client.loggedInAs or "unknown"
        return incoming_dir / f"recv_{username}_{transfer_id}.bin"

    def clear_stale_temp_files_for_user(self, username):
        if not username:
            return
        incoming_dir = Path(__file__).resolve().parents[2] / "runtime" / "incoming"
        incoming_dir.mkdir(parents=True, exist_ok=True)
        for filepath in incoming_dir.glob(f"recv_{username}_*.bin"):
            try:
                filepath.unlink()
            except OSError:
                pass

    def handle_packet(self, data, addr):

        packet_type = data[0]
        transfer_id = struct.unpack("!I", data[1:5])[0]
        
        if packet_type == self.DATA:
            self.handle_data_packet(data, addr)

        elif packet_type == self.END:
            self.handle_end_packet(addr, transfer_id)

        elif packet_type in (self.ACK, self.NACK):
            peer_ip, peer_port = addr
            self.handle_sender_feedback(data, peer_ip, peer_port)

    def retransmit(self, transfer_id, seq, peer_ip, peer_port):

        key = (transfer_id, seq)

        if key in self.sent_packet:
            packet = self.sent_packet[key]
            self.udp.send(packet, (peer_ip, peer_port))

    def initiate_udp_transfer(self, transfer_id, filepath, peer_ip, peer_port):
        thread = threading.Thread(
            target=self._send_file,
            args=(transfer_id, filepath, peer_ip, peer_port),
            daemon=True
        )
        thread.start()

    def _send_file(self, transfer_id, filepath, peer_ip, peer_port):

        file_path = Path(filepath)
        if not file_path.exists():
            print(f"File not found: {filepath}")
            return

        seq = 0
        with open(filepath, "rb") as f:
            while True:

                chunk = f.read(self.CHUNK_SIZE)

                if not chunk:
                    end_packet = struct.pack("!BII", self.END, transfer_id, seq)
                    self.udp.send(end_packet, (peer_ip, peer_port))
                    break

                packet = struct.pack("!BII", self.DATA, transfer_id, seq) + chunk

                self.sent_packet[(transfer_id, seq)] = packet

                self.udp.send(packet, (peer_ip, peer_port))

                seq += 1
                time.sleep(0.001)

    def handle_sender_feedback(self, data, peer_ip, peer_port):

        packet_type, transfer_id, seq = struct.unpack("!BII", data[:9])

        if packet_type == self.ACK:

            key = (transfer_id, seq)

            if key in self.sent_packet:
                del self.sent_packet[key]

        elif packet_type == self.NACK:
            self.retransmit(transfer_id, seq, peer_ip, peer_port)

    def receiver_send_ack(self, addr, transfer_id, seq):

        packet = struct.pack("!BII", self.ACK, transfer_id, seq)
        self.udp.send(packet, addr)

    def receiver_send_nack(self, addr, transfer_id, seq):

        packet = struct.pack("!BII", self.NACK, transfer_id, seq)
        self.udp.send(packet, addr)

    def handle_data_packet(self, data, addr):

        if len(data) < 9:
            print(f"[UDP] Packet too short from {addr}, ignoring")
            return

        packet_type, transfer_id, seq = struct.unpack("!BII", data[:9])
        chunk = data[9:]

        if seq == 1:
            self.client.interface.display("File transfer beginning!")

        key = (addr, transfer_id)

        if key not in self.recv_expected:
            temp_file_path = self._temp_bin_path(transfer_id)

            self.recv_expected[key] = 0
            self.recv_buffers[key] = {}
            self.recv_files[key] = open(temp_file_path, "wb")

        expected = self.recv_expected[key]
        buffer = self.recv_buffers[key]
        file = self.recv_files[key]

        if seq == expected:

            file.write(chunk)
            self.recv_expected[key] += 1

            self.receiver_send_ack(addr, transfer_id, seq)

            while self.recv_expected[key] in buffer:
                file.write(buffer.pop(self.recv_expected[key]))
                self.recv_expected[key] += 1

        elif seq > expected:

            buffer[seq] = chunk
            self.receiver_send_nack(addr, transfer_id, expected)

        else:

            self.receiver_send_ack(addr, transfer_id, seq)

    def handle_end_packet(self, addr, transfer_id):

        key = (addr, transfer_id)

        if key in self.recv_files:

            self.recv_files[key].close()

            temp_path = self._temp_bin_path(transfer_id)

            filename = self.recv_filenames.pop(transfer_id, f"recv_{transfer_id}.bin")

            final_path = Path.home() / "Downloads" / filename
            final_path.parent.mkdir(exist_ok=True)

            temp_path.replace(final_path)

            del self.recv_files[key]
            del self.recv_buffers[key]
            del self.recv_expected[key]

            self.client.interface.on_file_received(str(final_path))