import logging
import multiprocessing as mp
import pickle
import queue
import threading
from typing import Tuple, List

import click
import cv2 as cv
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

import robomaster as rm
from robomaster import CTX

QUEUE_SIZE: int = 10
PUSH_FREQUENCY: int = 1
TIMEOUT_UNIT: float = 0.1
QUEUE_TIMEOUT: float = TIMEOUT_UNIT / PUSH_FREQUENCY


def display(frame, **kwargs) -> None:
    cv.imshow("frame", frame)
    cv.waitKey(1)


def handle_event(cmd: rm.Commander, queues: Tuple[mp.Queue, ...], logger: logging.Logger) -> None:
    push_queue, event_queue = queues
    try:
        push = push_queue.get(timeout=QUEUE_TIMEOUT)
        logger.info('push: %s', push)
    except queue.Empty:
        pass

    try:
        event = event_queue.get(timeout=QUEUE_TIMEOUT)
        # safety first
        if type(event) == rm.ArmorHitEvent:
            cmd.chassis_speed(0, 0, 0)
        logger.info('event: %s', event)
    except queue.Empty:
        pass


class Controller:
    DELTA_SPEED: float = 0.2
    DELTA_DEGREE: float = 20

    def __init__(self, cmd: rm.Commander, logger: logging.Logger):
        self._mu = threading.Lock()
        self.cmd = cmd
        self.logger = logger
        self.v: List[float, float] = [0, 0]
        self.previous_v: List[float, float] = [0, 0]
        self.v_gimbal: List[float, float] = [0, 0]
        self.previous_v_gimbal: List[float, float] = [0, 0]
        self.ctrl_pressed: bool = False

    def on_press(self, key):
        with self._mu:
            if key == Key.ctrl:
                self.ctrl_pressed = True
                return
            if self.ctrl_pressed and key == KeyCode(char='c'):
                # stop listener
                self.v = [0, 0]
                self.v_gimbal = [0, 0]
                self.send_command()
                return False
            if key == Key.space:
                self.cmd.blaster_fire()
                return

            self.logger.debug('pressed: %s', key)
            if key == KeyCode(char='w'):
                self.v[0] = self.DELTA_SPEED
            elif key == KeyCode(char='s'):
                self.v[0] = -self.DELTA_SPEED
            elif key == KeyCode(char='a'):
                self.v[1] = -self.DELTA_SPEED
            elif key == KeyCode(char='d'):
                self.v[1] = self.DELTA_SPEED
            elif key == Key.up:
                self.v_gimbal[0] = self.DELTA_DEGREE
            elif key == Key.down:
                self.v_gimbal[0] = -self.DELTA_DEGREE
            elif key == Key.left:
                self.v_gimbal[1] = -self.DELTA_DEGREE
            elif key == Key.right:
                self.v_gimbal[1] = self.DELTA_DEGREE

            self.send_command()

    def on_release(self, key):
        with self._mu:
            if key == Key.ctrl:
                self.ctrl_pressed = False
                return

            self.logger.debug('released: %s', key)
            if key in (KeyCode(char='w'), KeyCode(char='s')):
                self.v[0] = 0
            elif key in (KeyCode(char='a'), KeyCode(char='d')):
                self.v[1] = 0
            elif key in (Key.up, Key.down):
                self.v_gimbal[0] = 0
            elif key in (Key.left, Key.right):
                self.v_gimbal[1] = 0

            self.send_command()

    def send_command(self):
        if self.v != self.previous_v:
            self.previous_v = [*self.v]
            self.logger.debug('chassis speed: x: %s, y: %s', self.v[0], self.v[1])
            self.cmd.chassis_speed(self.v[0], self.v[1], 0)
        if self.v_gimbal != self.previous_v_gimbal:
            self.logger.debug('gimbal speed: pitch: %s, yaw: %s', self.v_gimbal[0], self.v_gimbal[1])
            self.previous_v_gimbal = [*self.v_gimbal]
            self.cmd.gimbal_speed(self.v_gimbal[0], self.v_gimbal[1])


def control(cmd: rm.Commander, logger: logging.Logger, **kwargs) -> None:
    controller = Controller(cmd, logger)
    with keyboard.Listener(
            on_press=controller.on_press,
            on_release=controller.on_release) as listener:
        listener.join()


@click.command()
@click.option('--ip', default='', type=str, help='(Optional) IP of Robomaster EP')
@click.option('--timeout', default=10.0, type=float, help='(Optional) Timeout for commands')
def cli(ip: str, timeout: float):
    manager: mp.managers.SyncManager = CTX.Manager()

    hub = rm.Hub()
    cmd = rm.Commander(ip=ip, timeout=timeout)
    ip = cmd.get_ip()

    # reset
    cmd.robot_mode(rm.MODE_GIMBAL_LEAD)
    cmd.gimbal_recenter()

    # vision
    cmd.stream(True)
    hub.worker(rm.Vision, 'vision', (None, ip, display))

    # push and event
    cmd.chassis_push_on(PUSH_FREQUENCY, PUSH_FREQUENCY, PUSH_FREQUENCY)
    cmd.gimbal_push_on(PUSH_FREQUENCY)
    cmd.armor_sensitivity(10)
    cmd.armor_event(rm.ARMOR_HIT, True)
    cmd.sound_event(rm.SOUND_APPLAUSE, True)
    push_queue = manager.Queue(QUEUE_SIZE)
    event_queue = manager.Queue(QUEUE_SIZE)
    hub.worker(rm.PushListener, 'push', (push_queue,))
    hub.worker(rm.EventListener, 'event', (event_queue, ip))

    # push and event handler
    hub.worker(rm.Mind, 'event-handler', ((push_queue, event_queue), ip, handle_event))

    # controller
    hub.worker(rm.Mind, 'controller', ((), ip, control), {'loop': False})

    hub.run()


if __name__ == '__main__':
    pickle.DEFAULT_PROTOCOL = pickle.HIGHEST_PROTOCOL
    cli()
