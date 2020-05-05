import socket
import threading

VIDEO_PORT: int = 40921
AUDIO_PORT: int = 40922
CTRL_PORT: int = 40923
PUSH_PORT: int = 40924
EVENT_PORT: int = 40925
IP_PORT: int = 40926

DEFAULT_BUF_SIZE: int = 512

# switch_enum
SWITCH_ON: str = 'on'
SWITCH_OFF: str = 'off'

# mode_enum
MODE_CHASSIS_LEAD = 'chassis_lead'
MODE_GIMBAL_LEAD = 'gimbal_lead'
MODE_FREE = 'free'
MODE_ENUMS = (MODE_CHASSIS_LEAD, MODE_GIMBAL_LEAD, MODE_FREE)


def get_broadcast_ip(timeout: float = None) -> str:
    BROADCAST_INITIAL: str = 'robot ip '

    ip_listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip_listener.bind(('', IP_PORT))
    ip_listener.settimeout(timeout)
    msg, ip, port = None, None, None
    try:
        msg, (ip, port) = ip_listener.recvfrom(DEFAULT_BUF_SIZE)
    finally:
        ip_listener.close()
    msg = msg.decode()
    assert len(msg) > len(BROADCAST_INITIAL), f'broken msg from {ip}:{port}: {msg}'
    msg = msg[len(BROADCAST_INITIAL):]
    assert msg == ip, f'unmatched source({ip}) and reported IP({msg})'
    return msg


class Commander:
    def __init__(self, ip: str = '', timeout: float = 5):
        self._mu: threading.Lock = threading.Lock()
        with self._mu:
            if ip == '':
                ip = get_broadcast_ip(timeout)
            self._ip: str = ip
            self._closed: bool = False
            self._conn: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._timeout: float = timeout
            self._conn.settimeout(self._timeout)
            self._conn.connect((self._ip, CTRL_PORT))
            resp = self._do('command')
            assert self._is_ok(resp) or resp == 'Already in SDK mode', f'entering SDK mode: {resp}'

    def close(self):
        with self._mu:
            self._do()
            self._conn.close()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self):
        self.close()

    @staticmethod
    def _is_ok(resp: str) -> bool:
        return resp == 'ok'

    def _do(self, *args) -> str:
        assert len(args) > 0, 'empty arg not accepted'
        assert not self._closed, 'connection is already closed'
        cmd = ' '.join(map(str, args)) + ';'
        self._conn.send(cmd.encode())
        buf = self._conn.recv(DEFAULT_BUF_SIZE)
        return buf.decode()

    def version(self) -> str:
        """
        query robomaster SDK version
        :return: version string
        """
        with self._mu:
            return self._do('version')

    def robot_mode(self, mode: str):
        """
        机器人运动模式控制
        :param mode: 三种模式之一，见enum MODE_*
        """
        assert mode in MODE_ENUMS, f'unknown mode {mode}'
        with self._mu:
            resp = self._do('robot', 'mode', mode)
            assert self._is_ok(resp), f'robot_mode: {resp}'

    def get_robot_mode(self) -> str:
        """
        查询当前机器人运动模式
        :return: 三种模式之一，见enum MODE_*
        """
        with self._mu:
            resp = self._do('robot', 'mode', '?')
            assert resp in MODE_ENUMS, f'unexpected robot mode result: {resp}'
            return resp

    def chassis_speed(self, x: float = 0, y: float = 0, z: float = 0):
        assert -3.5 <= x <= 3.5, f'x {x} is out of range'
        assert -3.5 <= y <= 3.5, f'y {y} is out of range'
        assert -600 <= z <= 600, f'z {z} is out of range'
