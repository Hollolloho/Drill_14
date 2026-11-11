import time
running = False
stack = []

def change_mode(mode):
    if stack:
        stack.pop().finish()
    stack.append(mode)
    mode.init()


def push_mode(mode):
    if stack:
        stack[-1].pause()
    stack.append(mode)
    mode.init()


def pop_mode():
    if stack:
        stack.pop().finish()
    if stack:
        stack[-1].resume()
    else:
        quit()


def quit():
    global running
    running = False

frame_time = 0.0

def run(start_mode):
    global running, stack, frame_time
    running = True
    stack = [start_mode]
    frame_time = 0.0
    try:
        start_mode.init()
        previous_time = time.perf_counter()
        while running:
            current_time = time.perf_counter()
            frame_time = current_time - previous_time
            previous_time = current_time
            stack[-1].handle_events()
            stack[-1].update()
            stack[-1].render()
    finally:
        while stack:
            stack.pop().finish()
        running = False

# time.time()은 1970년 1월 1일 0시 0분 0초 UTC 이후 경과한 시간을 초 단위로 반환
# 게임을 설계할 때 게임 객체의 물리적 크기(어떤 면적에 있고 어느정도 크기 인지) 사전에 정의해야함
# 이를 응용해서 물리 식을 적용하여 게임 객체의 움직임을 계산
# ex) 게임월드의 면적은 10km X 10km 이런식
