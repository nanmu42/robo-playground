import socket
from unittest import TestCase
from unittest.mock import patch, Mock

import robomaster
from robomaster import Commander


class TestConnection(TestCase):
    def test_get_broadcast_ip(self):
        with patch.object(socket.socket, 'recvfrom', return_value=(b'robot ip 192.168.42.42', ('192.168.42.42', 40101))):
            ip = robomaster.get_broadcast_ip(2)
            self.assertEqual('192.168.42.42', ip)


class TestCommander(TestCase):
    @patch('socket.socket')
    def setUp(self, mock_socket):
        IP = '127.0.0.1'
        TIMEOUT = 42.1234

        m = mock_socket()
        m.recv.return_value = b'ok'
        self.commander = Commander(ip=IP, timeout=TIMEOUT)
        m.settimeout.assert_called_with(TIMEOUT)
        m.connect.assert_called_with((IP, robomaster.CTRL_PORT))
        m.recv.assert_called_with(robomaster.DEFAULT_BUF_SIZE)
        m.send.assert_called_with(b'command;')
        m.recv.assert_called_once()

    def test__is_ok(self):
        self.assertTrue(Commander._is_ok('ok'))
        self.assertFalse(Commander._is_ok('fail'))

    def test_version(self):
        VERSION = '1.2.3.4.5'

        with patch('robomaster.Commander._do', return_value=VERSION) as m:
            self.assertEqual(VERSION, self.commander.version())
            m.assert_called_with('version')
