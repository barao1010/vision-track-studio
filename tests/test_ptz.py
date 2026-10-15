import socket
import struct
import threading
import time
import unittest
from vtrack.ptz import Protocol, PTZSession, visca_move, visca_zoom, pelco


class PTZTests(unittest.TestCase):
    def test_visca_udp_packet_and_stop(self):
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.bind(('127.0.0.1', 0))
        receiver.settimeout(2)
        protocol = Protocol({'protocol': 'VISCA IP', 'host': '127.0.0.1', 'port': receiver.getsockname()[1]})
        try:
            protocol.move(.5, -.5, .5)
            packet, _ = receiver.recvfrom(1024)
            kind, length, sequence = struct.unpack('!HHI', packet[:8])
            self.assertEqual((kind, length, sequence), (0x100, 9, 1))
            self.assertEqual(packet[8:], bytes.fromhex('810106010c0a0202ff'))
            packet, _ = receiver.recvfrom(1024)
            self.assertEqual(packet[8:], visca_zoom(.5))
            protocol.move(0, 0, 0)
            packet, _ = receiver.recvfrom(1024)
            self.assertEqual(packet[8:][-3:], b'\x03\x03\xff')
        finally:
            protocol.close()
            receiver.close()

    def test_pelco_checksum_preset_and_motion(self):
        packet = pelco(.5, -.5, .5, address=2)
        self.assertEqual(packet[0], 255)
        self.assertEqual(packet[3], 2 | 16 | 32)
        self.assertEqual(packet[-1], sum(packet[1:-1]) & 255)
        self.assertEqual(pelco(address=2, preset=3, save=True), bytes.fromhex('ff020003000308'))
        with self.assertRaises(ValueError):
            visca_move(float('nan'), 0)

    def test_deadman_stops_without_fresh_commands(self):
        history = []
        class Fake:
            def __init__(self, config): pass
            def move(self, *velocity): history.append((time.monotonic(), velocity))
            def close(self): self.move(0, 0, 0)
            def preset(self, *args): pass
        session = PTZSession({}, Fake)
        try:
            session.move(.5, 0, 0)
            time.sleep(.5)
            self.assertTrue(any(command == (.5, 0, 0) for _, command in history))
            self.assertEqual(history[-1][1], (0, 0, 0))
        finally:
            session.close()
        self.assertFalse(session.worker.is_alive())
