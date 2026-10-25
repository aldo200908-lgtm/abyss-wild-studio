import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from motion_math import (W, H, CAPTION_Y, CAPTION_SAFE_WIDTH, MAX_CAPTION_TEXT_PX,
                         make_camera_plan, apply_motion_plans, validate_motion,
                         validate_captions, smooth, focal_point)


def beat(i, width, height, seconds=2.6):
    return {'beat': i, 'start': float(i * 3),
            'end': float(i * 3 + seconds),
            'asset': {'file': f'{i:02d}.jpg', 'type': 'image',
                      'id': f'asset-{i}', 'width': width, 'height': height}}


class CameraMotionTests(unittest.TestCase):
    def test_horizontals_alternate_even_with_zoom_interleaved(self):
        beats = [beat(0, 1920, 1080), beat(1, 1080, 1920),
                 beat(2, 1800, 1150), beat(3, 1000, 1000),
                 beat(4, 2500, 1000), beat(5, 1920, 1080)]
        apply_motion_plans(beats, 'Cualquier tema')
        self.assertEqual([b['camera']['direction'] for b in beats],
                         ['right', 'none', 'left', 'none', 'right', 'left'])
        self.assertEqual(validate_motion(beats), 4)

    def test_motion_has_easing_and_60_to_120_peak_speed(self):
        b = beat(0, 1800, 1000, seconds=2.84)
        camera = make_camera_plan(b, seed='La historia del mundo')
        self.assertEqual(camera['mode'], 'pan')
        peak = 1.5 * abs(camera['to_x'] - camera['from_x']) / 2.84
        self.assertGreaterEqual(peak, 60)
        self.assertLessEqual(peak, 120)
        self.assertAlmostEqual(smooth(0), 0)
        self.assertAlmostEqual(smooth(.5), .5)
        self.assertAlmostEqual(smooth(1), 1)
        self.assertLessEqual(camera['zoom_end'], 1.02)
        validate_motion([dict(b, camera=camera)])

    def test_zoom_portrait_square_never_pan(self):
        beats = [beat(0, 1080, 1920), beat(1, 1000, 1000)]
        apply_motion_plans(beats, 'Agujeros negros')
        self.assertEqual([b['camera']['mode'] for b in beats], ['zoom', 'zoom'])
        self.assertEqual([b['camera']['zoom_end'] for b in beats], [1.10, 1.10])
        self.assertEqual(validate_motion(beats), 0)

    def test_no_empty_edges_through_entire_motion(self):
        beats = [beat(i, 2400, 1300, seconds=2.85) for i in range(8)]
        apply_motion_plans(beats, 'Bioluminiscencia')
        self.assertEqual(validate_motion(beats), 8)
        bad = beats[0]['camera']
        bad['from_x'] += 400
        bad['to_x'] += 400
        with self.assertRaisesRegex(ValueError, 'borde horizontal vacío'):
            validate_motion(beats)

    def test_wide_picture_prefers_json_focus(self):
        b = beat(0, 3100, 1050)
        b['focal_point'] = {'x': .82, 'y': .28}
        plan = make_camera_plan(b)
        self.assertTrue(plan['wide_crop'])
        self.assertEqual(plan['focal_point'], {'x': .82, 'y': .28})

    def test_wide_picture_saliency_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'wide.jpg'
            im = Image.new('RGB', (2400, 600), '#333333')
            draw = ImageDraw.Draw(im)
            # More salient patch toward the right third.
            for x in range(1700, 2100, 20):
                draw.rectangle((x, 200, x + 9, 460), fill='white')
            im.save(p)
            point = focal_point(None, p, 4.0)
        self.assertGreater(point['x'], .60)
        self.assertGreaterEqual(point['y'], 0)
        self.assertLessEqual(point['y'], 1)

    def test_caption_center_and_single_word_width(self):
        layout = {'y': CAPTION_Y, 'max_width': CAPTION_SAFE_WIDTH,
                  'max_text_px': MAX_CAPTION_TEXT_PX}
        self.assertAlmostEqual(CAPTION_Y * H, 998.4, places=5)
        self.assertLessEqual(MAX_CAPTION_TEXT_PX + 12, CAPTION_SAFE_WIDTH * W)
        captions = [{'start': 0, 'end': .5,
                     'words': [{'start': 0, 'end': .5,
                                'text': 'electroencefalografista'}]}]
        self.assertEqual(validate_captions(captions, layout), 1)
        captions[0]['words'].append({'text': 'otro'})
        with self.assertRaisesRegex(ValueError, 'una sola palabra'):
            validate_captions(captions, layout)

    def test_pan_direction_validation_detects_repetition(self):
        beats = [beat(0, 1500, 1000), beat(1, 1600, 1000)]
        apply_motion_plans(beats, 'Prueba')
        beats[1]['camera']['direction'] = 'right'
        with self.assertRaisesRegex(ValueError, 'no alterna'):
            validate_motion(beats)

    def test_images_with_no_media_are_static(self):
        b = {'beat': 0, 'start': 0, 'end': 2.5, 'asset': None}
        b['camera'] = make_camera_plan(b)
        self.assertEqual(b['camera']['mode'], 'static')
        self.assertEqual(validate_motion([b]), 0)


if __name__ == '__main__':
    unittest.main()
