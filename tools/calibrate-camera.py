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
@click.argument('material', help='path to video containing ChAruco board')
@click.option('--gap', help='use every frame_gap-th frame in the video', type=int, default=30)
@click.option('--frame-num', help='how many frames to use in the video', type=int, default=30)
@click.option('-x', help='number of markers in X direction', type=int, default=9)
@click.option('-y', help='number of markers in Y direction', type=int, default=7)
@click.option('--marker-length', help='number of markers in Y direction', type=int, default=0.07)
@click.option('--square-length', help='number of markers in Y direction', type=int, default=0.09)
@click.option('-y', help='number of markers in Y direction', type=int, default=7)
def main(material: str, gap: int, frame_num: int, x: int, y: int, marker_length: int, square_length: int):
    cap = cv.VideoCapture(material)
    if not cap.isOpened():
        raise click.Abort('openCV VideoCapture failed')

    video_width = cap.get(cv.CAP_PROP_FRAME_WIDTH)
    video_height = cap.get(cv.CAP_PROP_FRAME_HEIGHT)

    dictionary = cv.aruco.DICT_APRILTAG_36h11
    board = cv.aruco_CharucoBoard(x, y, square_length, marker_length, dictionary)
    index: int = 0

    all_corners = []
    all_ids = []
    while True:
        index += 1
        ok, frame = cap.read()
        if not ok:
            click.echo('video ends')
            break
        if index % gap != 0:
            continue
        charuco_corners, charuco_ids = detect_corners(frame, board, dictionary)
        if charuco_corners is None:
            continue
        all_corners += charuco_corners
        all_ids += charuco_ids
        if index // gap >= frame_num:
            click.echo('enough frame num')
    cap.release()
    click.echo('calibrating...')
    camera_matrix = np.zeros((3,3))
    retval, camera_matrix, dist_coeffs, rvecs, tvecs = cv.aruco.calibrateCameraCharuco(all_corners, all_ids, board, (video_width, video_height), camera_matrix, None)
    click.echo('here it is:')
    click.echo(camera_matrix)
    click.echo(dist_coeffs)
    cv.destroyAllWindows()


if __name__ == '__main__':
    main()
