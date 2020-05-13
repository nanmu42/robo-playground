import cv2 as cv

import robomaster as rm


def display(frame):
    img = frame.to_nd_array()
    cv.imshow("Test", img)


def main():
    m = rm.Mind()
    r = rm.Commander(ip='192.168.31.56')

    r.stream(True)
    vision_queue = rm.CTX.Queue(8)
    vision = rm.Vision('vision', vision_queue, m.get_closed_event(), r.get_ip(), display)
    m.worker(vision)

    m.run()


if __name__ == '__main__':
    main()
