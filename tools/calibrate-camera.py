import glob
import os

import click
import cv2 as cv
import numpy as np


def detect_corners(frame, board, dictionary):
    corners, ids, rejected = cv.aruco.detectMarkers(frame, dictionary)
    corners, ids, rejected, recovered = cv.aruco.refineDetectedMarkers(frame, board, corners, ids, rejected)
    if corners is None or len(corners) == 0:
        return None, None
    retval, charuco_corners, charuco_ids = cv.aruco.interpolateCornersCharuco(corners, ids, frame, board)
    return charuco_corners, charuco_ids


@click.command()
@click.argument('folder')
@click.option('-x', help='number of markers in X direction', type=int, default=9)
@click.option('-y', help='number of markers in Y direction', type=int, default=7)
@click.option('--marker-length', help='number of markers in Y direction', type=float, default=0.015)
@click.option('--square-length', help='number of markers in Y direction', type=float, default=0.02)
@click.option('-y', help='number of markers in Y direction', type=int, default=7)
def main(folder: str, x: int, y: int, marker_length: int, square_length: int):
    images = glob.glob(os.path.join(folder, '*.png'))
    dictionary = cv.aruco.getPredefinedDictionary(cv.aruco.DICT_APRILTAG_36h11)
    board = cv.aruco.CharucoBoard_create(x, y, square_length, marker_length, dictionary)
    all_corners = []
    all_ids = []
    frame = None
    for image_path in images:
        frame = cv.imread(image_path)
        charuco_corners, charuco_ids = detect_corners(frame, board, dictionary)
        if charuco_corners is None or len(charuco_corners) < 4:
            continue
        all_corners.append(charuco_corners)
        all_ids.append(charuco_ids)
    width = frame.shape[1]
    height = frame.shape[0]
    click.echo('calibrating...')
    camera_matrix = np.zeros((3, 3))
    retval, camera_matrix, dist_coeffs, rvecs, tvecs = cv.aruco.calibrateCameraCharuco(all_corners, all_ids, board,
                                                                                       (width, height), camera_matrix,
                                                                                       None)
    click.echo('here it is:')
    click.echo(camera_matrix)
    click.echo(dist_coeffs)
    cv.destroyAllWindows()


if __name__ == '__main__':
    main()
