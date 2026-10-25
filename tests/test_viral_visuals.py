"""Headless FFmpeg visual regression for ABYSS WILD edutainment pipeline."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

from viral_visuals import (shot_ranges, prepare_image, image_ok, make_mascots,
                           mascot_events, verify_video)
from word_alignment import sync_words


class ViralVisualTests(unittest.TestCase):
    def test_shots_have_strict_three_to_four_seconds(self):
        for length in (30, 31.5, 37.0, 42.1, 45.0):
            with self.subTest(length=length):
                ranges=shot_ranges(length)
                self.assertEqual(ranges[0][0], 0)
                self.assertAlmostEqual(ranges[-1][1], length)
                self.assertTrue(all(3 <= b-a <= 4 for a,b in ranges))

    def test_reject_blank_image(self):
        with tempfile.TemporaryDirectory() as directory:
            blank=Path(directory)/'blank.png'
            Image.new('RGB',(720,1280),'#111111').save(blank)
            self.assertFalse(image_ok(blank))

    def test_mascot_variants_are_transparent_and_three(self):
        with tempfile.TemporaryDirectory() as directory:
            files=make_mascots(Path(directory))
            self.assertEqual(len(files),3)
            for file in files:
                with Image.open(Path(directory)/file) as im:
                    self.assertEqual(im.size,(440,520))
                    self.assertEqual(im.mode,'RGBA')
                    self.assertEqual(im.getpixel((0,0))[3],0)
                    self.assertGreater(im.getpixel((220,240))[3],0)
            events=mascot_events(37)
            self.assertEqual(len(events),3)
            self.assertEqual(events[0]['start'],0)
            self.assertEqual(events[0]['end'],3)
            self.assertTrue(all(e['end']<=37 for e in events))

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),
                         'FFmpeg required')
    def test_black_video_is_rejected_even_when_resolution_is_correct(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'black.mp4'
            subprocess.run(['ffmpeg','-loglevel','error','-y','-f','lavfi',
                            '-i','color=c=black:s=1080x1920:r=30:d=3',
                            '-c:v','libx264','-preset','ultrafast',
                            str(path)],check=True)
            with self.assertRaisesRegex(RuntimeError, 'Fotograma vacío'):
                verify_video(path,3)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),
                         'FFmpeg required')
    def test_zoompan_ffmpeg_outputs_filled_portrait_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.png'
            result=Path(directory)/'shot.mp4'
            im=Image.new('RGB',(720,1200),'#155064')
            draw=ImageDraw.Draw(im)
            for i in range(18):
                draw.rectangle((i*40,0,i*40+20,1200),fill=(
                    10+i*10,30+i*7,70+i*6))
            draw.ellipse((150,270,530,740),fill='#f5db74')
            im.save(source)
            prepare_image(source,result,3.0,0)
            self.assertTrue(result.stat().st_size>10000)
            verify_video(result,3.0)


class WordAlignmentTests(unittest.TestCase):
    def test_asr_word_offsets_follow_real_whisper_timestamps(self):
        marks=[{'text':'La','start':0,'end':.2},
               {'text':'Titanoboa','start':.2,'end':1.0},
               {'text':'medía','start':1.0,'end':1.5},
               {'text':'catorce','start':1.5,'end':2.2},
               {'text':'metros','start':2.2,'end':3.0}]
        observed=[{'text':'La','start':.05,'end':.18},
                  {'text':'Titanoboa','start':.2,'end':.9},
                  {'text':'medía','start':.95,'end':1.3},
                  {'text':'14','start':1.35,'end':1.7},
                  {'text':'metros','start':1.75,'end':2.1}]
        aligned, stats=sync_words(marks,observed,3.0)
        self.assertEqual(len(aligned),5)
        self.assertEqual(stats['matched_ratio'],1.0)
        self.assertEqual(aligned[3]['start'],1.35)
        self.assertEqual(aligned[4]['start'],1.75)

    def test_no_whisper_offsets_returns_measured_tts_fallback(self):
        marks=[{'text':'Titanoboa','start':0,'end':.5}]
        result,stats=sync_words(marks,[],1)
        self.assertEqual(result,marks)
        self.assertEqual(stats['matched_ratio'],0)


if __name__=='__main__':
    unittest.main()
