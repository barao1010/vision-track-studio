# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise real loopback transports; never contacts physical camera hardware."""
import socket
import struct
import unittest
from protocol_drivers import WirePTZ


class LoopbackProtocolTests(unittest.TestCase):
    def test_visca_udp_move_and_watchdog_stop_reach_receiver(self):
        receiver=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        receiver.bind(('127.0.0.1',0));receiver.settimeout(2)
        driver=WirePTZ({'protocol':'visca_ip','host':'127.0.0.1','port':receiver.getsockname()[1]})
        try:
            startup=[receiver.recv(1024),receiver.recv(1024)]
            driver.move(.5,-.2,0)
            move=[receiver.recv(1024),receiver.recv(1024)]
            stopped=[receiver.recv(1024),receiver.recv(1024)]
            packets=startup+move+stopped
            headers=[struct.unpack('>HHI',p[:8]) for p in packets]
            self.assertTrue(all(kind==0x100 and length==len(p)-8 for (kind,length,_),p in zip(headers,packets)))
            self.assertEqual([h[2] for h in headers],list(range(1,7)))
            self.assertEqual(stopped[0][8:],bytes.fromhex('81 01 06 01 01 01 03 03 ff'))
            self.assertEqual(stopped[1][8:],bytes.fromhex('81 01 04 07 00 ff'))
        finally:
            driver.close();receiver.close()

    def test_pelco_tcp_stop_is_transmitted_after_move_timeout(self):
        listener=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(2)
        driver=WirePTZ({'protocol':'pelco_d','host':'127.0.0.1','port':listener.getsockname()[1]})
        connection,_=listener.accept();connection.settimeout(2)
        def packet():
            data=b''
            while len(data)<7:
                block=connection.recv(7-len(data))
                if not block: raise AssertionError('Transport closed before a full command arrived')
                data+=block
            return data
        try:
            self.assertEqual(packet()[3],0)
            driver.move(.5,0,.5)
            moving=packet();stopped=packet()
            self.assertEqual(moving[3],0x22)
            self.assertEqual(stopped[3],0)
            for value in [moving,stopped]: self.assertEqual(value[6],sum(value[1:6])%256)
        finally:
            driver.close();connection.close();listener.close()
