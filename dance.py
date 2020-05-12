import robomaster as rm
import cv2 as cv


def display(frame):
    img = frame.to_nd_array()
    cv.imshow("Test", img)


def main():
    r = rm.Mind(ip='192.168.31.56')

    vision_queue = rm.CTX.Queue(8)
    vision = rm.Vision(vision_queue, r.get_closed_event(),r.cmd.get_ip(), display)
    r.cmd.stream(True)
    r.worker('video', vision)

    r.run()


if __name__ == '__main__':
    main()
