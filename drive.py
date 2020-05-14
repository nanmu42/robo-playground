import pickle

import cv2 as cv

import robomaster as rm


def display(frame):
    cv.imshow("frame", frame)
    cv.waitKey(1)


def main():
    pickle.DEFAULT_PROTOCOL = pickle.HIGHEST_PROTOCOL

    m = rm.Mind()
    r = rm.Commander(ip='192.168.31.56')

    r.stream(True)
    vision_queue = rm.CTX.Queue(3)
    m.worker(rm.Vision, 'vision', (vision_queue, r.get_ip(), display))

    m.run()


if __name__ == '__main__':
    main()
