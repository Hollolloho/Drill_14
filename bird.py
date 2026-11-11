"""실제 이동 거리에 날갯짓을 맞추는 새."""

from pico2d import get_canvas_height, get_canvas_width, load_image

import game_framework

PIXELS_PER_METER = 10.0 / 0.3
FLIGHT_SPEED_KMPH = 18.0
FLIGHT_SPEED_MPS = FLIGHT_SPEED_KMPH / 3.6
FLIGHT_SPEED_PPS = FLIGHT_SPEED_MPS * PIXELS_PER_METER
WINGBEAT_DISTANCE_M = 2.5
WINGBEAT_DISTANCE_PX = WINGBEAT_DISTANCE_M * PIXELS_PER_METER

FRAME_COLUMNS = 5
FRAME_COUNT = 14  # 마지막 행의 오른쪽 끝은 빈 칸이다.
SOURCE_COLUMN_WIDTH = 182  # 원본 오른쪽의 8픽셀은 여백이다.
SOURCE_ROW_BOUNDS = (0, 180, 352, 506)
SOURCE_BEAK_Y = (103, 264, 442)
DRAW_WIDTH = 92
DRAW_SCALE = DRAW_WIDTH / SOURCE_COLUMN_WIDTH
FLOCK_SIZE = 10


def frame_clip(frame, image_height):
    """불규칙한 원본 행 범위를 pico2d의 아래쪽 원점으로 변환한다."""
    row, column = divmod(int(frame) % FRAME_COUNT, FRAME_COLUMNS)
    top, bottom = SOURCE_ROW_BOUNDS[row:row + 2]
    return column * SOURCE_COLUMN_WIDTH, image_height - bottom, SOURCE_COLUMN_WIDTH, bottom - top


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

    def advance(self, dt):
        if dt <= 0:
            return
        distance = FLIGHT_SPEED_PPS * dt
        span = self.right - self.left
        offset = self.x - self.left
        # 왕복 경로를 펼친 뒤 접으면 여러 경계를 넘어도 이동량을 잃지 않는다.
        progress = offset if self.direction > 0 else 2 * span - offset
        progress = (progress + distance) % (2 * span)
        self.x = self.left + min(progress, 2 * span - progress)
        self.direction = 1 if progress < span else -1
        # 순변위가 아니라 실제 이동 거리로 계산해 반사 때도 날갯짓을 이어 간다.
        self.frame = (
            self.frame + distance / WINGBEAT_DISTANCE_PX * FRAME_COUNT
        ) % FRAME_COUNT

    def update(self):
        self.advance(game_framework.frame_time)

    def draw(self):
        clip = frame_clip(self.frame, self.image.h)
        row = int(self.frame) // FRAME_COLUMNS
        source_center_y = self.image.h - clip[1] - clip[3] / 2
        # 행별 부리 높이를 맞추고 모든 프레임을 같은 비율로 축소한다.
        draw_y = self.y + (SOURCE_BEAK_Y[row] - source_center_y) * DRAW_SCALE
        self.image.clip_composite_draw(
            *clip, 0, 'h' if self.direction < 0 else '',
            self.x, draw_y, DRAW_WIDTH, clip[3] * DRAW_SCALE,
        )


def create_flock():
    """하늘의 두 줄에 다섯 마리씩 배치하고 날갯짓 시작 시점을 분산한다."""
    width, height = get_canvas_width(), get_canvas_height()
    birds = []
    for index in range(FLOCK_SIZE):
        row, column = divmod(index, 5)
        birds.append(Bird(
            width * (column + 1) / 6,
            height * (0.65 + row * 0.17),
            direction=1 if row == 0 else -1,
            frame=index * FRAME_COUNT / FLOCK_SIZE,
        ))
    return birds
