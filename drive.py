import logging
import multiprocessing as mp
import pickle
import queue
import threading
from typing import Tuple

import click
import cv2 as cv
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

import robomaster as rm

QUEUE_SIZE: int = 3


def display(frame, **kwargs) -> None:
    cv.imshow("frame", frame)
    cv.waitKey(1)


def handle_event(cmd: rm.Commander, queues: Tuple[mp.Queue, ...], logger: logging.Logger) -> None:
    push_queue, event_queue = queues
    try:
        push = push_queue.get_nowait()
        logger.info('push: %s', push)
    except queue.Empty:
        pass

    try:
        event = event_queue.get()
        # safety first
        if type(event) == rm.ArmorHitEvent:
            cmd.chassis_wheel(0, 0, 0, 0)
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
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.vz: float = 0.0
        self.v_pitch: float = 0.0

    def on_press(self, key):
        with self._mu:
            if key == Key.space:
                self.cmd.blaster_fire()
                return

            self.logger.debug('pressed: %s', key)
            if key == KeyCode(char='w'):
                self.vx = self.DELTA_SPEED
            elif key == KeyCode(char='s'):
                self.vx = -self.DELTA_SPEED
            elif key == KeyCode(char='a'):
                self.vy = -self.DELTA_SPEED
            elif key == KeyCode(char='d'):
                self.vy = self.DELTA_SPEED
            elif key == Key.up:
                self.v_pitch = self.DELTA_DEGREE
            elif key == Key.down:
                self.v_pitch = -self.DELTA_DEGREE
            elif key == Key.left:
                self.vz = -self.DELTA_DEGREE
            elif key == Key.right:
                self.vz = self.DELTA_DEGREE

            self.send_command()

    def on_release(self, key):
        with self._mu:
            if key == Key.esc:
                # stop listener
                self.vx: float = 0.0
                self.vy: float = 0.0
                self.vz: float = 0.0
                self.v_pitch: float = 0.0
                self.send_command()
                return False

            self.logger.debug('released: %s', key)
            if key in (KeyCode(char='w'), KeyCode(char='s')):
                self.vx = 0
            elif key in (KeyCode(char='a'), KeyCode(char='d')):
                self.vy = 0
            elif key in (Key.up, Key.down):
                self.v_pitch = 0
            elif key in (Key.left, Key.right):
                self.vz = 0

            self.send_command()

    def send_command(self):
        self.logger.debug('x: %s, y: %s, z: %s, pitch: %s', self.vx, self.vy, self.vz, self.v_pitch)
        if not any((self.vx, self.vy, self.vz)):
            self.cmd.chassis_wheel(0, 0, 0, 0)
        else:
            self.cmd.chassis_speed(self.vx, self.vy, self.vz)
        self.cmd.gimbal_speed(self.v_pitch, 0)


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
    hub = rm.Hub()
    cmd = rm.Commander(ip=ip, timeout=timeout)
    ip = cmd.get_ip()

    # vision
    cmd.stream(True)
    hub.worker(rm.Vision, 'vision', (None, ip, display))

    # push and event
    cmd.chassis_push_on(1, 1, 1)
    cmd.gimbal_push_on(1)
    cmd.armor_event(rm.ARMOR_HIT, True)
    cmd.sound_event(rm.SOUND_APPLAUSE, True)
    push_queue = rm.CTX.Queue(QUEUE_SIZE)
    event_queue = rm.CTX.Queue(QUEUE_SIZE)
    hub.worker(rm.PushListener, 'push', (push_queue,))
    hub.worker(rm.EventListener, 'event', (event_queue, ip))

    # push and event handler
    hub.worker(rm.Mind, 'event-handler', ((push_queue, event_queue), ip, handle_event))

    # controller
    cmd.robot_mode(rm.MODE_CHASSIS_LEAD)
    hub.worker(rm.Mind, 'controller', ((), ip, control))

    hub.run()


if __name__ == '__main__':
    pickle.DEFAULT_PROTOCOL = pickle.HIGHEST_PROTOCOL
    cli()
