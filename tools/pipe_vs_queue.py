"""
Modified from:
https://stackoverflow.com/questions/48353601/multiprocessing-pipe-is-even-slower-than-multiprocessing-queue/48394435
"""

import sys
import time
from multiprocessing import Process, Pipe, Queue

import numpy as np

NUM = 20000


def worker_pipe(conn):
    for task_nbr in range(NUM):
        conn.send(np.random.rand(40, 40, 3))
    sys.exit(1)


def main_pipe(duplex: bool):
    parent_conn, child_conn = Pipe(duplex=duplex)
    Process(target=worker_pipe, args=(child_conn,)).start()
    for num in range(NUM):
        message = parent_conn.recv()


def pipe_test_no_duplex():
    start_time = time.time()
    main_pipe(False)
    end_time = time.time()
    duration = end_time - start_time
    msg_per_sec = NUM / duration
    print("Pipe(no duplex)")
    print("Duration: " + str(duration))
    print("Messages Per Second: " + str(msg_per_sec))


def pipe_test_duplex():
    start_time = time.time()
    main_pipe(True)
    end_time = time.time()
    duration = end_time - start_time
    msg_per_sec = NUM / duration
    print("Pipe(duplex)")
    print("Duration: " + str(duration))
    print("Messages Per Second: " + str(msg_per_sec))


def worker_queue(q):
    for task_nbr in range(NUM):
        q.put(np.random.rand(40, 40, 3))
    sys.exit(1)


def main_queue():
    recv_q = Queue()
    Process(target=worker_queue, args=(recv_q,)).start()
    for num in range(NUM):
        message = recv_q.get()


def queue_test():
    start_time = time.time()
    main_queue()
    end_time = time.time()
    duration = end_time - start_time
    msg_per_sec = NUM / duration
    print("Queue")
    print("Duration: " + str(duration))
    print("Messages Per Second: " + str(msg_per_sec))


if __name__ == "__main__":
    for i in range(2):
        print()
        queue_test()
        print()
        pipe_test_duplex()
        print()
        pipe_test_no_duplex()
