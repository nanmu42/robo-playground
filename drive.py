import logging
import multiprocessing as mp
import pickle
import threading
from typing import Tuple

import click
import cv2 as cv
from pynput import keyboard
from pynput.keyboard import Key

import robomaster as rm

QUEUE_SIZE: int = 3


def display(frame) -> None:
    cv.imshow("frame", frame)
    cv.waitKey(1)


def handle_event(cmd: rm.Commander, queues: Tuple[mp.Queue, ...], logger: logging.Logger) -> None:
    push_queue, event_queue = queues
    push = push_queue.get()
    # safety first
    if type(push) == rm.ArmorHitEvent:
        cmd.chassis_wheel(0, 0, 0, 0)

    logger.info('push: %s', push)
    logger.info('event: %s', event_queue.get())


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

            if key == 'w':
                self.vx += self.DELTA_SPEED
            elif key == 's':
                self.vx -= self.DELTA_SPEED
            elif key == 'a':
                self.vy -= self.DELTA_SPEED
            elif key == 'd':
                self.vy += self.DELTA_SPEED
            elif key == Key.up:
                self.v_pitch += self.DELTA_DEGREE
            elif key == Key.down:
                self.v_pitch -= self.DELTA_DEGREE
            elif key == Key.left:
                self.vz -= self.DELTA_DEGREE
            elif key == Key.right:
                self.vz += self.DELTA_DEGREE

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

            if key == 'w':
                self.vx -= self.DELTA_SPEED
            elif key == 's':
                self.vx += self.DELTA_SPEED
            elif key == 'a':
                self.vy += self.DELTA_SPEED
            elif key == 'd':
                self.vy -= self.DELTA_SPEED
            elif key == Key.up:
                self.v_pitch -= self.DELTA_DEGREE
            elif key == Key.down:
                self.v_pitch += self.DELTA_DEGREE
            elif key == Key.left:
                self.vz += self.DELTA_DEGREE
            elif key == Key.right:
                self.vz -= self.DELTA_DEGREE

            self.send_command()

    def send_command(self):
        self.cmd.chassis_speed(self.vx, self.vy, self.vz)
        self.cmd.gimbal_speed(self.v_pitch, 0)


def control(cmd: rm.Commander, logger: logging.Logger) -> None:
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
    hub.worker(rm.Vision, 'vision', (None, cmd.get_ip(), display))

    # push and event
    cmd.chassis_push_on(1, 1, 1)
    cmd.gimbal_push_on(1)
    cmd.armor_event(rm.ARMOR_HIT, True)
    cmd.armor_event(rm.SOUND_APPLAUSE, True)
    push_queue = rm.CTX.Queue(QUEUE_SIZE)
    event_queue = rm.CTX.Queue(QUEUE_SIZE)
    hub.worker(rm.PushListener, 'push', (push_queue,))
    hub.worker(rm.EventListener, 'event', (event_queue,))

    # push and event handler
    hub.worker(rm.Mind, 'event-handler', ((push_queue, event_queue), ip, handle_event))

    # controller
    hub.worker(rm.Mind, 'controller', ((), ip, control))

    hub.run()


if __name__ == '__main__':
    pickle.DEFAULT_PROTOCOL = pickle.HIGHEST_PROTOCOL
    cli()
