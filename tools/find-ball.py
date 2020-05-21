import math
from typing import Tuple, List

import click
import cv2 as cv
import numpy as np

GREEN_LOWER = (29, 90, 90)
GREEN_UPPER = (64, 255, 255)
BALL_ACTUAL_RADIUS = 0.065 / 2
FOCAL_LENGTH_HD = 710
HORIZONTAL_DEGREES = 96
VERTICAL_DEGREES = 54


def distance_decomposition(pixel_x: float, distance: float) -> Tuple[float, float]:
    horizontal_degree = HORIZONTAL_DEGREES * (pixel_x / 1280 - 0.5)
    rad = horizontal_degree / 180 * math.pi
    lateral_distance = distance * math.sin(rad)
    forward_distance = distance * math.cos(rad)
    return forward_distance, lateral_distance


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

    return (x, y), radius


@click.group()
@click.option('-i', type=click.Path(exists=True))
@click.pass_context
def cli(ctx: click.Context, i: str):
    ctx.ensure_object(dict)
    ctx.obj['image_path']: str = i


@cli.command()
@click.argument('distance', type=float)
@click.option('--ball-radius', type=float, help='(Optional) ball radius in meter', default=BALL_ACTUAL_RADIUS)
@click.pass_context
def focal_length(ctx: click.Context, distance: float, ball_radius: float):
    frame = cv.imread(ctx.obj['image_path'])
    _, pixel_radius = process(frame)
    f: float = distance * pixel_radius / ball_radius
    click.echo(f'focal length: {f}')
    cv.waitKey(0)
    cv.destroyAllWindows()


@cli.command()
@click.option('--focal-length', type=float, help='(Optional) focal length under 720p', default=FOCAL_LENGTH_HD)
@click.option('--ball-radius', type=float, help='(Optional) ball radius in meter', default=BALL_ACTUAL_RADIUS)
@click.pass_context
def position(ctx: click.Context, focal_length: float, ball_radius: float):
    frame = cv.imread(ctx.obj['image_path'])
    (pixel_x, _), pixel_radius = process(frame)
    d = focal_length * ball_radius / pixel_radius
    margin = - focal_length * ball_radius / math.pow(pixel_radius, 2)
    click.echo(f'focal length: {d}, margin for 1px: {margin}, radius in pixel: {pixel_radius}')

    forward_distance, lateral_distance = distance_decomposition(pixel_x, d)
    click.echo(f'position: forward {forward_distance}, lateral {lateral_distance}')

    cv.waitKey(0)
    cv.destroyAllWindows()


if __name__ == '__main__':
    cli(obj={})
