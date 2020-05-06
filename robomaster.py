import socket
import threading
from dataclasses import dataclass

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


@dataclass
class ChassisSpeed:
    x: float
    y: float
    z: float
    w1: int
    w2: int
    w3: int
    w4: int


@dataclass
class ChassisPosition:
    x: float
    y: float
    z: float


@dataclass
class ChassisAttitude:
    pitch: float
    roll: float
    yaw: float


@dataclass
class ChassisStatus:
    # 是否静止
    static: bool
    # 是否上坡
    uphill: bool
    # 是否下坡
    downhill: bool
    # 是否溜坡
    on_slope: bool
    # 是否被拿起
    pick_up: bool
    # 是否滑行
    slip: bool
    # x轴是否感应到撞击
    impact_x: bool
    # y轴是否感应到撞击
    impact_y: bool
    # z轴是否感应到撞击
    impact_z: bool
    # 是否翻车
    roll_over: bool
    # 是否在坡上静止
    hill_static: bool


@dataclass
class GimbalAttitude:
    pitch: float
    yaw: float


def get_broadcast_ip(timeout: float = None) -> str:
    """
    接收广播以获取机甲IP

    :param timeout: 等待超时（秒）
    :return: 机甲IP地址
    """
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

    def do(self, *args) -> str:
        """
        执行任意命令
        :param args: 命令内容，list
        :return: 命令返回
        """
        with self._mu:
            return self._do(*args)

    def version(self) -> str:
        """
        query robomaster SDK version

        :return: version string
        """
        return self.do('version')

    def robot_mode(self, mode: str) -> str:
        """
        机器人运动模式控制

        :param mode: 三种模式之一，见enum MODE_*
        :return: ok，否则raise
        """
        assert mode in MODE_ENUMS, f'unknown mode {mode}'
        resp = self.do('robot', 'mode', mode)
        assert self._is_ok(resp), f'robot_mode: {resp}'
        return resp

    def get_robot_mode(self) -> str:
        """
        查询当前机器人运动模式

        :return: 三种模式之一，见enum MODE_*
        """
        resp = self.do('robot', 'mode', '?')
        assert resp in MODE_ENUMS, f'unexpected robot mode result: {resp}'
        return resp

    def chassis_speed(self, x: float = 0, y: float = 0, z: float = 0) -> str:
        """
        控制底盘运动速度

        :param x: x 轴向运动速度，单位 m/s
        :param y: y 轴向运动速度，单位 m/s
        :param z: z 轴向旋转速度，单位 °/s
        :return: ok，否则raise
        """
        assert -3.5 <= x <= 3.5, f'x {x} is out of range'
        assert -3.5 <= y <= 3.5, f'y {y} is out of range'
        assert -600 <= z <= 600, f'z {z} is out of range'
        resp = self.do('chassis', 'speed', 'x', x, 'y', y, 'z', z)
        assert self._is_ok(resp), f'chassis_speed: {resp}'
        return resp

    def get_chassis_speed(self) -> ChassisSpeed:
        """
        获取底盘速度信息

        :return: x 轴向运动速度(m/s)，
        y 轴向运动速度(m/s)，z 轴向旋转速度(°/s)，
        w1 右前麦轮速度(rpm)，w2 左前麦轮速速(rpm)，
        w3 右后麦轮速度(rpm)，w4 左后麦轮速度(rpm)
        """
        resp = self.do('chassis', 'speed', '?')
        ans = resp.split(' ')
        assert len(ans) == 7, f'get_chassis_speed: {resp}'
        return ChassisSpeed(x=float(ans[0]), y=float(ans[1]), z=float(ans[2]), w1=int(ans[3]), w2=int(ans[4]), w3=int(ans[5]), w4=int(ans[6]))

    def chassis_wheel(self, w1: int = 0, w2: int = 0, w3: int = 0, w4: int = 0) -> str:
        """
        底盘轮子速度控制

        :param w1: 右前麦轮速度，单位 rpm
        :param w2: 左前麦轮速度，单位 rpm
        :param w3: 右后麦轮速度，单位 rpm
        :param w4: 左后麦轮速度，单位 rpm
        :return ok: ok，否则raise
        """
        for i, v in enumerate((w1, w2, w3, w4)):
            assert -1000 <= v <= 1000, f'w{i + 1} {v} is out of range'
        resp = self.do('chassis', 'wheel', 'w1', w1, 'w2', w2, 'w3', w3, 'w4', w4)
        assert self._is_ok(resp), f'chassis_wheel: {resp}'
        return resp

    def chassis_move(self, x: float = 0, y: float = 0, z: int = 0, speed_xy: float = None, speed_z: float = None) -> str:
        """
        控制底盘运动当指定位置，坐标轴原点为当前位置

        :param x: x 轴向运动距离，单位 m
        :param y: y 轴向运动距离，单位 m
        :param z: z 轴向旋转角度，单位 °
        :param speed_xy: xy 轴向运动速度，单位 m/s
        :param speed_z: z 轴向旋转速度， 单位 °/s
        :return ok: ok，否则raise
        """
        assert -5 <= x <= 5, f'x {x} is out of range'
        assert -5 <= y <= 5, f'y {y} is out of range'
        assert -1800 <= z <= 1800, f'z {z} is out of range'
        assert speed_xy is None or 0 < speed_xy <= 3.5, f'speed_xy {speed_xy} is out of range'
        assert speed_z is None or 0 < speed_z <= 600, f'speed_z {speed_z} is out of range'
        cmd = ['chassis', 'move', 'x', x, 'y', y, 'z', z]
        if speed_xy is not None:
            cmd += ['vxy', speed_xy]
        if speed_z is not None:
            cmd += ['vz', speed_z]
        resp = self.do(*cmd)
        assert self._is_ok(resp), f'chassis_move: {resp}'
        return resp

    def get_chassis_position(self) -> ChassisPosition:
        """
        获取底盘当前的位置(以上电时刻位置为原点)

        :return: x 轴位置(m)，y 轴位置(m)，偏航角度(°)
        """
        resp = self.do('chassis', 'position', '?')
        ans = resp.split(' ')
        assert len(ans) == 3, f'get_chassis_position: {resp}'
        return ChassisPosition(float(ans[0]), float(ans[1]), float(ans[2]))

    def get_chassis_attitude(self) -> ChassisAttitude:
        """
        获取底盘姿态信息

        :return: pitch 轴角度(°)，roll 轴角度(°)，yaw 轴角度(°)
        """
        resp = self.do('chassis', 'attitude', '?')
        ans = resp.split(' ')
        assert len(ans) == 3, f'get_chassis_attitude: {resp}'
        return ChassisAttitude(float(ans[0]), float(ans[1]), float(ans[2]))

    def get_chassis_status(self) -> ChassisStatus:
        """
        获取底盘状态信息

        :return: 底盘状态，详见 ChassisStatus
        """
        resp = self.do('chassis', 'status', '?')
        ans = resp.split(' ')
        assert len(ans) == 11, f'get_chassis_status: {resp}'
        return ChassisStatus(*map(lambda x: bool(int(x)), ans))

    def chassis_push_on(self, position_freq: int = None, attitude_freq: int = None, status_freq: int = None, all_freq: int = None) -> str:
        """
        打开底盘中相应属性的信息推送，支持的频率 1, 5, 10, 20, 30, 50

        :param position_freq: 位置推送频率，不开启则设为None
        :param attitude_freq: 姿态推送频率，不开启则设为None
        :param status_freq: 状态推送频率，不开启则设为None
        :param all_freq: 统一设置所有推送频率，设置则开启所有推送
        :return: ok，否则raise
        """
        valid_frequencies = (1, 5, 10, 20, 30, 50)
        cmd = ['chassis', 'push']
        if all_freq is not None:
            assert all_freq in valid_frequencies, f'all_freq {all_freq} is not valid'
            cmd += ['freq', all_freq]
        else:
            if position_freq is not None:
                assert position_freq in valid_frequencies, f'position_freq {position_freq} is not valid'
                cmd += ['position', SWITCH_ON, 'pfreq', position_freq]
            if attitude_freq is not None:
                assert attitude_freq in valid_frequencies, f'attitude_freq {attitude_freq} is not valid'
                cmd += ['attitude', SWITCH_ON, 'afreq', attitude_freq]
            if status_freq is not None:
                assert status_freq in valid_frequencies, f'status_freq {status_freq} is not valid'
                cmd += ['status', SWITCH_ON, 'sfreq', status_freq]
        assert len(cmd) > 2, 'at least one argument should not be None'
        resp = self.do(*cmd)
        assert self._is_ok(resp), f'chassis_push_on: {resp}'
        return resp

    def chassis_push_off(self, position: bool = False, attitude: bool = False, status: bool = False, all: bool = False) -> str:
        """
        关闭底盘中相应属性的信息推送。

        :param position: 是否关闭位置推送
        :param attitude: 是否关闭姿态推送
        :param status: 是否关闭状态推送
        :param all: 关闭所有推送
        :return: ok，否则raise
        """
        cmd = ['chassis', 'push']
        if all or position:
            cmd += ['position', SWITCH_OFF]
        if all or attitude:
            cmd += ['attitude', SWITCH_OFF]
        if all or status:
            cmd += ['status', SWITCH_OFF]

        assert len(cmd) > 2, 'at least one argument should be True'
        resp = self.do(*cmd)
        assert self._is_ok(resp), f'chassis_push_off: {resp}'
        return resp

    def gimbal_speed(self, pitch: float, yaw: float) -> str:
        """
        控制云台运动速度

        :param pitch: pitch 轴速度，单位 °/s
        :param yaw: yaw 轴速度，单位 °/s
        :return: ok，否则raise
        """
        assert -450 <= pitch <= 450, f'pitch {pitch} is out of range'
        assert -450 <= yaw <= 450, f'yaw {yaw} is out of range'
        resp = self.do('gimbal', 'speed', 'p', pitch, 'y', yaw)
        assert self._is_ok(resp), f'gimbal_speed: {resp}'
        return resp

    def gimbal_move(self, pitch: float = 0, yaw: float = 0, pitch_speed: float = None, yaw_speed: float = None) -> str:
        """
        控制云台运动到指定位置，坐标轴原点为当前位置

        :param pitch: pitch 轴角度， 单位 °
        :param yaw: yaw 轴角度， 单位 °
        :param pitch_speed: pitch 轴运动速速，单位 °/s
        :param yaw_speed: yaw 轴运动速速，单位 °/s
        :return: ok，否则raise
        """
        assert -55 <= pitch <= 55, f'pitch {pitch} is out of range'
        assert -55 <= yaw <= 55, f'yaw {yaw} is out of range'
        assert pitch_speed is None or 0 < pitch_speed <= 540, f'pitch_speed {pitch_speed} is out of range'
        assert yaw_speed is None or 0 < yaw_speed <= 540, f'yaw_speed {yaw_speed} is out of range'
        cmd = ['gimbal', 'move', 'p', pitch, 'y', yaw]
        if pitch_speed is not None:
            cmd += ['vp', pitch_speed]
        if yaw_speed is not None:
            cmd += ['vy', yaw_speed]
        resp = self.do(*cmd)
        assert self._is_ok(resp), f'gimbal_move: {resp}'
        return resp

    def gimbal_moveto(self, pitch: float = 0, yaw: float = 0, pitch_speed: float = None, yaw_speed: float = None) -> str:
        """
        控制云台运动到指定位置，坐标轴原点为上电位置

        :param pitch: pitch 轴角度， 单位 °
        :param yaw: yaw 轴角度， 单位 °
        :param pitch_speed: pitch 轴运动速速，单位 °/s
        :param yaw_speed: yaw 轴运动速速，单位 °/s
        :return: ok，否则raise
        """
        assert -25 <= pitch <= 30, f'pitch {pitch} is out of range'
        assert -250 <= yaw <= 250, f'yaw {yaw} is out of range'
        assert pitch_speed is None or 0 < pitch_speed <= 540, f'pitch_speed {pitch_speed} is out of range'
        assert yaw_speed is None or 0 < yaw_speed <= 540, f'yaw_speed {yaw_speed} is out of range'
        cmd = ['gimbal', 'moveto', 'p', pitch, 'y', yaw]
        if pitch_speed is not None:
            cmd += ['vp', pitch_speed]
        if yaw_speed is not None:
            cmd += ['vy', yaw_speed]
        resp = self.do(*cmd)
        assert self._is_ok(resp), f'gimbal_moveto: {resp}'
        return resp

    def gimbal_suspend(self):
        """
        使云台进入休眠状态
        :return: ok，否则raise
        """
        resp = self.do('gimbal', 'suspend')
        assert self._is_ok(resp), f'gimbal_suspend: {resp}'
        return resp

    def gimbal_resume(self):
        """
        控制云台从休眠状态中恢复
        :return: ok，否则raise
        """
        resp = self.do('gimbal', 'resume')
        assert self._is_ok(resp), f'gimbal_resume: {resp}'
        return resp

    def gimbal_recenter(self):
        """
        控制云台回中
        :return: ok，否则raise
        """
        resp = self.do('gimbal', 'recenter')
        assert self._is_ok(resp), f'gimbal_recenter: {resp}'
        return resp

    def get_gimbal_attitude(self) -> GimbalAttitude:
        """
        获取云台姿态信息
        :return: pitch 轴角度(°)，yaw 轴角度(°)
        """
        resp = self.do('gimbal', 'attitude', '?')
        ans = resp.split(' ')
        assert len(ans) == 2, f'get_gimbal_attitude: {resp}'
        return GimbalAttitude(pitch=float(ans[0]), yaw=float(ans[1]))

    def gimbal_push_on(self, attitude_freq: int = 5) -> str:
        """
        打开云台中相应属性的信息推送，支持的频率 1, 5, 10, 20, 30, 50

        :param attitude_freq: 姿态推送频率
        :return: ok，否则raise
        """
        valid_frequencies = (1, 5, 10, 20, 30, 50)
        assert attitude_freq in valid_frequencies, f'invalid attitude_freq {attitude_freq}'
        resp = self.do('gimbal', 'push', 'attitude', SWITCH_ON, 'afreq', attitude_freq)
        assert self._is_ok(resp), f'gimbal_push_on: {resp}'
        return resp

    def gimbal_push_off(self, attitude: bool = True) -> str:
        """
        关闭云台中相应属性的信息推送

        :param attitude: 关闭姿态推送
        :return: ok，否则raise
        """
        assert attitude, 'at least one augment should be True'
        resp = self.do('gimbal', 'push', 'attitude', SWITCH_OFF)
        assert self._is_ok(resp), f'gimbal_push_off: {resp}'
        return resp
