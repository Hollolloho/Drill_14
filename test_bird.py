"""그래픽 창 없이 비행 거리, 프레임, 경계와 게임 연결을 검증한다."""

import unittest
import struct
from pathlib import Path
from unittest.mock import Mock, patch

import bird
import game_framework
import game_world
import play_mode


class BirdTests(unittest.TestCase):
    def setUp(self):
        self.image = Mock(w=918, h=506)
        self.loader = Mock(return_value=self.image)
        replacements = patch.multiple(
            bird, load_image=self.loader,
            get_canvas_width=lambda: 1600, get_canvas_height=lambda: 600,
        )
        replacements.start()
        self.addCleanup(replacements.stop)
        shared_image = patch.object(bird.Bird, 'image', None)
        shared_image.start()
        self.addCleanup(shared_image.stop)

    def assert_same_state(self, actual, expected):
        self.assertAlmostEqual(actual.x, expected.x, places=7)
        self.assertEqual(actual.direction, expected.direction)
        # 순환 위상에서는 0과 14 직전이 서로 가깝다.
        delta = (actual.frame - expected.frame + 7) % 14 - 7
        self.assertAlmostEqual(delta, 0, places=7)

    def test_all_fourteen_clips_and_direction(self):
        subject = bird.Bird(300, 400)
        self.assertEqual(bird.frame_clip(0, 506), (0, 326, 182, 180))
        self.assertEqual(bird.frame_clip(13, 506), (546, 0, 182, 154))
        self.assertEqual(bird.frame_clip(14, 506), bird.frame_clip(0, 506))
        for frame in range(14):
            clip = bird.frame_clip(frame, 506)
            left, bottom, width, height = clip
            self.assertTrue(0 <= left < left + width <= 918)
            self.assertTrue(0 <= bottom < bottom + height <= 506)
            self.assertFalse(bottom == 0 and left >= 728)
            for direction, flip in ((1, ''), (-1, 'h')):
                subject.frame, subject.direction = frame + 0.5, direction
                subject.draw()
                draw_y = 400 + (bird.SOURCE_BEAK_Y[frame // 5] - (506 - bottom - height / 2)) * bird.DRAW_SCALE
                self.image.clip_composite_draw.assert_called_with(
                    *clip, 0, flip, 300, draw_y, 92, height * bird.DRAW_SCALE,
                )

    def test_clips_include_complete_sprites_without_adjacent_fragments(self):
        # 원본 PNG의 알파 영역을 측정한 범위다. 단순 균등 분할의 잘림을 잡는다.
        sprite_bounds = [
            (34, 1, 180, 144), (216, 2, 362, 143), (398, 12, 544, 142),
            (555, 17, 726, 139), (728, 48, 910, 136), (34, 217, 180, 335),
            (216, 216, 362, 340), (398, 216, 544, 336), (580, 217, 726, 326),
            (762, 219, 908, 329), (34, 392, 180, 500), (216, 394, 362, 500),
            (376, 395, 544, 483), (546, 370, 726, 484),
        ]
        png = Path(__file__).with_name('bird_animation.png').read_bytes()
        self.assertEqual(struct.unpack('>II', png[16:24]), (918, 506))
        for frame, (x0, y0, x1, y1) in enumerate(sprite_bounds):
            left, bottom, width, height = bird.frame_clip(frame, 506)
            top = 506 - bottom - height
            self.assertTrue(left <= x0 < x1 <= left + width)
            self.assertTrue(top <= y0 < y1 <= top + height)
            for other, (a, b, c, d) in enumerate(sprite_bounds):
                if other != frame:
                    self.assertTrue(c <= left or a >= left + width or d <= top or b >= top + height)

    def test_distance_and_wingbeat_use_the_same_scale(self):
        subject = bird.Bird(300, 400)
        subject.advance(0.25)
        self.assertAlmostEqual(subject.x, 300 + 125 / 3)
        self.assertAlmostEqual(subject.frame, 7)
        subject.advance(0.25)
        self.assertAlmostEqual(subject.x, 300 + 250 / 3)
        self.assertAlmostEqual(subject.frame, 0)
        self.assertEqual(subject.y, 400)

    def test_zero_or_negative_elapsed_time_does_not_move(self):
        subject = bird.Bird(300, 400, -1, 3.5)
        subject.advance(0)
        subject.advance(-1)
        self.assertEqual((subject.x, subject.direction, subject.frame), (300, -1, 3.5))

    def test_exact_edges_reverse_and_keep_remaining_distance(self):
        for x, direction, edge in ((1544, 1, 1554), (56, -1, 46)):
            with self.subTest(direction=direction):
                subject = bird.Bird(x, 400, direction)
                subject.advance(10 / bird.FLIGHT_SPEED_PPS)
                self.assertAlmostEqual(subject.x, edge)
                self.assertEqual(subject.direction, -direction)
                subject.advance(20 / bird.FLIGHT_SPEED_PPS)
                self.assertAlmostEqual(subject.x, edge - direction * 20)
                self.assertAlmostEqual(subject.frame, 30 / (250 / 3) * 14)

    def test_one_update_can_cross_many_edges(self):
        subject = bird.Bird(46, 400)
        subject.advance((4 * 1508 + 25) / bird.FLIGHT_SPEED_PPS)
        self.assertAlmostEqual(subject.x, 71)
        self.assertEqual(subject.direction, 1)
        self.assertAlmostEqual(subject.frame, ((4 * 1508 + 25) / (250 / 3) * 14) % 14)

    def test_equal_elapsed_time_at_different_frame_rates(self):
        duration = 30.125
        expected = bird.Bird(500, 400, -1, 2.25)
        expected.advance(duration)
        for fps in (30, 60, 144):
            with self.subTest(fps=fps):
                subject = bird.Bird(500, 400, -1, 2.25)
                count = int(duration * fps)
                for _ in range(count):
                    subject.advance(1 / fps)
                    self.assertTrue(subject.left <= subject.x <= subject.right)
                subject.advance(duration - count / fps)
                self.assert_same_state(subject, expected)
        subject = bird.Bird(500, 400, -1, 2.25)
        steps = [0.001, 0.249, 1.875, 17.5, 10.5]
        self.assertEqual(sum(steps), duration)
        for dt in steps:
            subject.advance(dt)
        self.assert_same_state(subject, expected)

    def test_ten_visible_birds_share_one_image(self):
        flock = bird.create_flock()
        self.assertEqual(len(flock), 10)
        self.assertEqual(len({(item.x, item.y) for item in flock}), 10)
        self.assertEqual(len({item.frame for item in flock}), 10)
        self.loader.assert_called_once_with('bird_animation.png')
        for item in flock:
            self.assertIs(item.image, self.image)
            self.assertTrue(46 <= item.x <= 1554)
            self.assertTrue(52 <= item.y <= 600 - 52)

    def test_play_mode_registers_updates_and_cleans_the_flock(self):
        game_world.clear()
        self.addCleanup(play_mode.finish)
        with patch.object(play_mode, 'Boy'), patch.object(play_mode, 'Grass'):
            for _ in range(2):
                play_mode.init()
                objects = [item for layer in game_world.world for item in layer]
                flock = [item for item in objects if isinstance(item, bird.Bird)]
                self.assertEqual(len(objects), 12)
                self.assertEqual(len(flock), 10)
                start_x = flock[0].x
                with patch.object(game_framework, 'frame_time', 0.25):
                    game_world.update()
                self.assertAlmostEqual(flock[0].x - start_x, 125 / 3)
                game_world.render()
                play_mode.finish()
                self.assertTrue(all(not layer for layer in game_world.world))
                self.assertIsNone(play_mode.boy)


class FrameTimingTests(unittest.TestCase):
    def test_current_monotonic_delta_is_available_before_update(self):
        observed = []
        mode = Mock()

        def update():
            observed.append(game_framework.frame_time)
            if len(observed) == 2:
                game_framework.quit()

        mode.update.side_effect = update
        with patch.object(game_framework.time, 'perf_counter', side_effect=[100, 100, 100.25]):
            game_framework.run(mode)
        self.assertEqual(observed, [0, 0.25])
        mode.finish.assert_called_once()
        self.assertFalse(game_framework.running)
        self.assertEqual(game_framework.stack, [])


if __name__ == '__main__':
    unittest.main()
