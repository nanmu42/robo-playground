import enum
import logging
import math
import multiprocessing as mp
import pickle
import queue
import time
from typing import Tuple, List, Optional

import click
import cv2 as cv
import simple_pid

import measure
import robomaster as rm
from robomaster import CTX

rm.LOG_LEVEL = logging.DEBUG
pickle.DEFAULT_PROTOCOL = pickle.HIGHEST_PROTOCOL

GREEN_LOWER = (29, 90, 90)
GREEN_UPPER = (64, 255, 255)
BALL_ACTUAL_RADIUS = 0.065 / 2

QUEUE_TIMEOUT: float = 0.5


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
    MAX_EVENT_LAPSE: float = 20 / 1000.0  # in seconds
    DEFAULT_XY_SPEED: float = 2.0
    DEFAULT_Z_SPEED: float = 180.0
    BALL_ABSENT_TIMEOUT: float = 8.0
    KICK_TIMEOUT: float = 0.3
    CHASE_ENTER_FORWARD_THRESHOLD: float = 1.2
    CHASE_EXIT_FORWARD_THRESHOLD: float = 1.4
    DEGREE_EPS: float = 2.0  # in degrees
    DISTANCE_EPS: float = 0.01  # in meters
    SLEEP_SECONDS: float = 1.0

    def __init__(self, name: str, ip: str,
                 vision: mp.Queue, push: mp.Queue, event: mp.Queue,
                 field_width: float, field_depth: float, timeout: float = 10):
        super().__init__(name, None, None, (ip, 0), timeout, True)
        self._state: KeeperState = KeeperState.WATCHING
        self._max_y = field_width / 2.0
        self._max_x = field_depth / 2.0
        self._vision = vision
        self._push = push
        self._event = event
        self._y_pid: simple_pid.PID = simple_pid.PID(-10, -0.05, -0.5, setpoint=0, sample_time=1 / 30, output_limits=(-self.DEFAULT_XY_SPEED, self.DEFAULT_XY_SPEED))

        # dynamic states
        self._position: rm.ChassisPosition = rm.ChassisPosition(0, 0, 0)
        self._position_last_seen: Optional[float] = None
        self._ball_distances: Optional[Tuple[float, float, float]] = None
        self._ball_last_seen: Optional[float] = None
        self._armor_hit_id: Optional[int] = None
        self._armor_hit_last_seen: Optional[float] = None

        self._cmd = rm.Commander(ip, timeout)
        self._cmd.robot_mode(rm.MODE_CHASSIS_LEAD)
        self._cmd.gimbal_moveto(pitch=-10)

        self._init_state()

    def close(self):
        self._cmd.close()
        super().close()

    def _next_state(self):
        self._state: KeeperState = self._state.next()
        self._init_state()

    def _reset_state(self):
        if self._state == KeeperState.WATCHING:
            return
        self._state: KeeperState = self._state.origin()
        self._init_state()

    def _init_state(self):
        if self._state == KeeperState.WATCHING:
            self._recenter_to_field()
            self._cmd.led_control(rm.LED_ALL, rm.LED_EFFECT_PULSE, 0, 255, 0)
        elif self._state == KeeperState.CHASING:
            self._y_pid.reset()
            self._cmd.led_control(rm.LED_ALL, rm.LED_EFFECT_SOLID, 255, 0, 0)
        elif self._state == KeeperState.KICKING:
            self._cmd.chassis_move(-self._max_x * 2 / 3, speed_xy=self.DEFAULT_XY_SPEED)
            self._cmd.led_control(rm.LED_ALL, rm.LED_EFFECT_SOLID, 255, 255, 255)
        else:
            raise ValueError(f'unknown state {self._state}')

    def _drain_vision(self):
        updated: bool = False
        while not self.closed:
            try:
                self._ball_distances = self._vision.get_nowait()
                updated = True
            except queue.Empty:
                if updated:
                    self._ball_last_seen = time.time()
                return

    def _drain_push(self):
        updated: bool = False
        while not self.closed:
            try:
                push = self._push.get_nowait()
                updated = True
                if type(push) == rm.ChassisPosition:
                    self._position.x, self._position.y = push.x, push.y
                elif type(push) == rm.ChassisAttitude:
                    self._position.z = push.yaw
                else:
                    raise ValueError(f'unexpected push content: {push}')
            except queue.Empty:
                if updated:
                    self._position_last_seen = time.time()
                return

    def _drain_event(self):
        updated: bool = False
        while not self.closed:
            try:
                hit = self._event.get_nowait()
                updated = True
                if type(hit) == rm.ArmorHitEvent:
                    self._armor_hit_id = hit.index
                else:
                    raise ValueError(f'unexpected event content: {hit}')
            except queue.Empty:
                if updated:
                    self._ball_last_seen = time.time()
                return

    def _recenter_to_field(self):
        diff_z = 0 if math.fabs(self._position.z) < self.DEGREE_EPS else self._position.z
        self._cmd.chassis_move(-self._position.x, -self._position.y, -diff_z, speed_xy=self.DEFAULT_XY_SPEED, speed_z=self.DEFAULT_Z_SPEED)

    def _watch(self):
        if self._ball_distances is None:
            return
        forward = self._ball_distances[0]
        if forward < self.CHASE_ENTER_FORWARD_THRESHOLD:
            self._next_state()

    def _chase_kick_check(self) -> bool:
        # hit events
        if self._armor_hit_id is not None:
            self._cmd.chassis_wheel(0, 0, 0, 0)

            if self._armor_hit_id == 2:
                if self._state == KeeperState.KICKING:
                    time.sleep(self.SLEEP_SECONDS)
                self._next_state()
                return False

            time.sleep(self.SLEEP_SECONDS)
            self._reset_state()
            return False

        # timeout
        now = time.time()
        if now - self._ball_last_seen > self.BALL_ABSENT_TIMEOUT:
            self._reset_state()
            return False

        # distances
        forward, lateral, horizontal_degree = self._ball_distances
        if forward > self.CHASE_EXIT_FORWARD_THRESHOLD:
            self._reset_state()
            return False

        # position
        if math.fabs(self._position.x) > self._max_x:
            self._cmd.chassis_wheel(0, 0, 0, 0)
            self._cmd.led_control(rm.LED_BOTTOM_FRONT, rm.LED_EFFECT_BLINK, 0, 0, 255)
            self._cmd.led_control(rm.LED_BOTTOM_BACK, rm.LED_EFFECT_BLINK, 0, 0, 255)
            return False

        if self._position.y > self._max_y and lateral > self.DISTANCE_EPS:
            self._cmd.chassis_wheel(0, 0, 0, 0)
            self._cmd.led_control(rm.LED_BOTTOM_RIGHT, rm.LED_EFFECT_BLINK, 0, 0, 255)
            return False
        if self._position.y < -self._max_y and -lateral > self.DISTANCE_EPS:
            self._cmd.chassis_wheel(0, 0, 0, 0)
            self._cmd.led_control(rm.LED_BOTTOM_LEFT, rm.LED_EFFECT_BLINK, 0, 0, 255)
            return False

        return True

    def _chase(self):
        ok = self._chase_kick_check()
        if not ok:
            return

        forward, lateral, horizontal_degree = self._ball_distances
        # can not see ball now
        if forward < 0.25:
            self._cmd.chassis_wheel(0, 0, 0, 0)
            return
        vy = self._y_pid(lateral)
        vy = 0 if math.fabs(vy) < 0.1 else vy
        if vy != 0:
            self._cmd.chassis_speed(y=vy)
        else:
            self._cmd.chassis_wheel(0, 0, 0, 0)

    def _kick(self):
        ok = self._chase_kick_check()
        if not ok:
            return

        now = time.time()
        if now - self._ball_last_seen > self.KICK_TIMEOUT:
            return

        forward, lateral, horizontal_degree = self._ball_distances
        vy = self._y_pid(lateral)
        vy = 0 if math.fabs(vy) < 0.1 else vy
        if vy != 0:
            self._cmd.chassis_speed(x=self.DEFAULT_XY_SPEED, y=vy)
        else:
            self._cmd.chassis_speed(x=self.DEFAULT_XY_SPEED)

    def _draw_graph(self):
        pass

    def _tick(self):
        self._armor_hit_last_seen = None
        self._armor_hit_id = None

        self._drain_push()
        self._drain_event()
        self._drain_vision()

    def work(self) -> None:
        self._tick()

        if self._state == KeeperState.WATCHING:
            self._watch()
        elif self._state == KeeperState.CHASING:
            self._chase()
        elif self._state == KeeperState.KICKING:
            self._kick()
        else:
            raise ValueError(f'unknown state {self._state}')


def contour_analysis(cnt) -> Tuple[int, int]:
    approx = cv.approxPolyDP(cnt, 0.01 * cv.arcLength(cnt, True), True)
    area = cv.contourArea(cnt)
    return len(approx), area


def biggest_circle_cnt(cnts: List):
    found_cnt = None
    found_edges = 0
    found_area = 0

    for cnt in cnts:
        edges, area = contour_analysis(cnt)
        if edges > 8 \
                and 260 < area < 20000 \
                and edges > found_edges \
                and area > found_area:
            found_edges = edges
            found_area = area
            found_cnt = cnt

    return found_cnt


def vision(frame, logger: logging.Logger) -> Optional[Tuple[float, float]]:
    processed = cv.GaussianBlur(frame, (11, 11), 0)
    processed = cv.cvtColor(processed, cv.COLOR_BGR2HSV)

    mask = cv.inRange(processed, GREEN_LOWER, GREEN_UPPER)
    mask = cv.morphologyEx(mask, cv.MORPH_OPEN, None)
    cnts, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    ball_cnt = biggest_circle_cnt(cnts)
    if ball_cnt is None:
        cv.putText(frame, 'no ball detected', (50, 20), cv.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 2)
        cv.imshow('vision', frame)
        cv.waitKey(1)
        return None

    (x, y), pixel_radius = cv.minEnclosingCircle(ball_cnt)
    distance = measure.pinhole_distance(BALL_ACTUAL_RADIUS, pixel_radius)
    forward, lateral = measure.distance_decomposition(x, distance)
    cv.circle(frame, (x, y), pixel_radius, (0, 255, 0), 2)
    cv.circle(frame, (x, y), 1, (0, 0, 255), 2)
    cv.putText(frame, 'forward: %.1f cm' % forward * 100, (50, 20), cv.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 2)
    cv.putText(frame, 'lateral: %.1f cm' % lateral * 100, (50, 70), cv.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 2)

    cv.imshow('vision', frame)
    cv.waitKey(1)

    return forward, lateral


@click.group()
@click.option('--ip', default='', type=str, help='(Optional) IP of Robomaster EP')
@click.option('--timeout', default=10.0, type=float, help='(Optional) Timeout for commands')
@click.option('--max-width', default=1.0, type=float, help='(Optional) Field width')
@click.option('--max-depth', default=1.0, type=float, help='(Optional) Field depth')
@click.pass_context
def cli(ctx: click.Context, ip: str, timeout: float, max_width: float, max_depth: float):
    ctx.ensure_object(dict)
    ctx.obj['manager']: mp.managers.SyncManager = CTX.Manager()
    ctx.obj['ip']: str = ip
    ctx.obj['timeout']: float = timeout
    ctx.obj['max_width']: float = max_width
    ctx.obj['max_depth']: float = max_depth


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
