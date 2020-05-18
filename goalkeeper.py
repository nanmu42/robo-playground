import enum
import logging
import multiprocessing as mp
import pickle

import click
import cv2 as cv
import simple_pid

import robomaster as rm
from robomaster import CTX

rm.LOG_LEVEL = logging.DEBUG
pickle.DEFAULT_PROTOCOL = pickle.HIGHEST_PROTOCOL


@enum.unique
class KeeperState(enum.IntEnum):
    _BEGIN = 0
    WATCHING = 1
    CHASING = 2
    KICKING = 3
    _END = 4

    def next(self):
        next_value = self + 1
        if next_value >= self._END:
            return KeeperState(self._BEGIN + 1)
        return KeeperState(next_value)

    def origin(self):
        return KeeperState(self._BEGIN + 1)


class KeeperMind(rm.Worker):
    PID_PARAMS = (-1, -0.1, -0.05)

    def __init__(self, name: str, ip: str,
                 vision: mp.Queue, push: mp.Queue, event: mp.Queue,
                 field_width: float, field_depth: float, timeout: float = 10):
        super().__init__(name, None, None, (ip, 0), timeout, True)
        self._state: KeeperState = KeeperState.WATCHING
        self._field_width = field_width
        self._field_depth = field_depth
        self._vision = vision
        self._push = push
        self._event = event
        self._logger = self.get_logger()
        self._pid: simple_pid.PID = simple_pid.PID(*self.PID_PARAMS, setpoint=0, sample_time=1 / 30, output_limits=(0, 2.5))
        self._position: rm.ChassisPosition = rm.ChassisPosition(0, 0, 0)

        self._cmd = rm.Commander(ip, timeout)
        self._cmd.gimbal_moveto(-10)

        self._init_state()

    def close(self):
        self._cmd.close()
        super().close()

    def _next_state(self):
        self._state: KeeperState = self._state.next()
        self._init_state()

    def _init_state(self):
        if self._state == KeeperState.WATCHING:
            self._cmd.led_control(rm.LED_ALL, rm.LED_EFFECT_PULSE, 0, 255, 0)
        elif self._state == KeeperState.CHASING:
            self._pid.reset()
            self._cmd.led_control(rm.LED_ALL, rm.LED_EFFECT_BLINK, 0, 0, 255)
        elif self._state == KeeperState.KICKING:
            self._cmd.led_control(rm.LED_ALL, rm.LED_EFFECT_SOLID, 255, 255, 255)
        else:
            raise ValueError(f'unknown state {self._state}')

    def _watch(self):
        pass

    def _chase(self):
        pass

    def _kick(self):
        pass

    def _update(self):
        pass

    def work(self) -> None:
        self._update()

        if self._state == KeeperState.WATCHING:
            self._watch()
        elif self._state == KeeperState.CHASING:
            self._chase()
        elif self._state == KeeperState.KICKING:
            self._kick()
        else:
            raise ValueError(f'unknown state {self._state}')


def vision(frame, **kwargs) -> None:
    cv.imshow("frame", frame)
    cv.waitKey(1)


@click.group()
@click.option('--ip', default='', type=str, help='(Optional) IP of Robomaster EP')
@click.option('--timeout', default=10.0, type=float, help='(Optional) Timeout for commands')
@click.option('--width', default=1.0, type=float, help='(Optional) Field width')
@click.option('--depth', default=1.0, type=float, help='(Optional) Field depth')
def cli(ctx: click.Context, ip: str, timeout: float, width: float, depth: float):
    ctx.ensure_object(dict)
    ctx.obj['manager']: mp.managers.SyncManager = CTX.Manager()
    ctx.obj['ip']: str = ip
    ctx.obj['timeout']: float = timeout
    ctx.obj['width']: float = width
    ctx.obj['depth']: float = depth


@cli.command()
@click.pass_context
def ensure_field(ctx: click.Context):
    pass


@cli.command()
@click.pass_context
def play(ctx: click.Context):
    pass


if __name__ == '__main__':
    cli(obj={})
