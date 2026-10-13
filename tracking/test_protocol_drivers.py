import unittest
import threading
from protocol_drivers import WirePTZ

class ProtocolTests(unittest.TestCase):
    def driver(self, kind):
        d = WirePTZ.__new__(WirePTZ)
        d.kind, d.address = kind, 1
        d.lock = threading.Lock()
        d.pan_invert = d.tilt_invert = False
        d.deadline = None
        d.packets = []
        d._send = d.packets.append
        return d

    def test_visca_stop_is_two_separate_commands(self):
        d = self.driver('visca_ip')
        d.stop()
        self.assertEqual(2, len(d.packets))
        self.assertEqual(bytes.fromhex('81 01 06 01 01 01 03 03 ff'), d.packets[0])
        self.assertEqual(bytes.fromhex('81 01 04 07 00 ff'), d.packets[1])

    def test_visca_image_up_maps_to_physical_up(self):
        d = self.driver('visca_ip')
        d.move(0, -.5, 0)
        self.assertEqual(1, d.packets[0][7])
        self.assertIsNotNone(d.deadline)

    def test_pelco_combines_zoom_and_pan_with_valid_checksum(self):
        d = self.driver('pelco_d')
        d.move(.5, 0, .5)
        packet = d.packets[0]
        self.assertEqual(0x22, packet[3])
        self.assertEqual(sum(packet[1:6]) % 256, packet[6])

    def test_presets_clear_continuous_motion_timeout(self):
        d = self.driver('visca_serial')
        d.move(.5, 0, 0)
        d.preset(3)
        self.assertIsNone(d.deadline)
        self.assertEqual(bytes.fromhex('81 01 04 3f 02 03 ff'), d.packets[-1])
