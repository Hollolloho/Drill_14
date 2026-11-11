"""실제 이동 거리에 날갯짓을 맞추는 새."""

from pico2d import get_canvas_width, load_image

PIXELS_PER_METER = 10.0 / 0.3
FLIGHT_SPEED_KMPH = 18.0
FLIGHT_SPEED_MPS = FLIGHT_SPEED_KMPH / 3.6
FLIGHT_SPEED_PPS = FLIGHT_SPEED_MPS * PIXELS_PER_METER
WINGBEAT_DISTANCE_M = 2.5
WINGBEAT_DISTANCE_PX = WINGBEAT_DISTANCE_M * PIXELS_PER_METER

FRAME_COLUMNS = 5
FRAME_ROWS = 3
FRAME_COUNT = 14  # 마지막 행의 오른쪽 끝은 빈 칸이다.
DRAW_WIDTH = 92
DRAW_HEIGHT = 84


def frame_clip(frame, image_width, image_height):
    """위에서 아래로 읽은 프레임을 pico2d의 아래쪽 원점으로 변환한다."""
    row, column = divmod(int(frame) % FRAME_COUNT, FRAME_COLUMNS)
    left = column * image_width // FRAME_COLUMNS
    right = (column + 1) * image_width // FRAME_COLUMNS
    top = row * image_height // FRAME_ROWS
    bottom = (row + 1) * image_height // FRAME_ROWS
    return left, image_height - bottom, right - left, bottom - top


class Bird:
    image = None

    def __init__(self, x, y, direction=1, frame=0.0):
        if Bird.image is None:
            Bird.image = load_image('bird_animation.png')
        self.x, self.y = x, y
        self.direction = direction
        self.frame = frame % FRAME_COUNT
        self.left = DRAW_WIDTH / 2
        self.right = get_canvas_width() - DRAW_WIDTH / 2
