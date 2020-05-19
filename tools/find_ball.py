from typing import Tuple, List

import click
import cv2 as cv
import numpy as np

GREEN_LOWER = (29, 90, 90)
GREEN_UPPER = (64, 255, 255)


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


def process(frame: np.ndarray):
    processed = cv.GaussianBlur(frame, (11, 11), 0)
    processed = cv.cvtColor(processed, cv.COLOR_BGR2HSV)

    mask = cv.inRange(processed, GREEN_LOWER, GREEN_UPPER)
    mask = cv.morphologyEx(mask, cv.MORPH_OPEN, None)
    cv.imshow('mask', mask)
    cnts, _ = cv.findContours(mask, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

    ball_cnt = biggest_circle_cnt(cnts)
    assert ball_cnt is not None, 'failed to find ball'

    (x, y), radius = cv.minEnclosingCircle(ball_cnt)
    cv.circle(frame, (int(x), int(y)), int(radius), (0, 255, 0), 2)
    cv.circle(frame, (int(x), int(y)), 1, (0, 0, 255), 2)

    cv.imshow('circle', frame)


@click.command()
@click.argument('image-path', type=click.Path(exists=True))
def cli(image_path: str):
    frame = cv.imread(image_path)
    process(frame)
    cv.waitKey(0)
    cv.destroyAllWindows()


if __name__ == '__main__':
    cli()
