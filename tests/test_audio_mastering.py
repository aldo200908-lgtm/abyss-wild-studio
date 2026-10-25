"""AAC true-peak regression: validate decoded MP4, not just loudnorm claims."""
import math
import re
import shutil
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np

import pipeline


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),
                     'FFmpeg/ffprobe needed for encoded AAC regression')
class MasteringAudioTests(unittest.TestCase):
    def test_decoder_peak_and_loudness_both_meet_publication_limits(self):
        sample_rate = 44100
        length = 6
        count = sample_rate * length
        t = np.arange(count) / sample_rate
        signal = .14 * np.sin(2 * np.pi * 210 * t) + \
                 .04 * np.sin(2 * np.pi * 290 * t)
        # High-energy transitions simulate loud consonants and impact effects.
        for index in range(1, length):
            start = index * sample_rate
            seq = np.arange(8820)
            signal[start:start + len(seq)] += .83 * \
                np.sin(2 * np.pi * 1300 * seq / sample_rate) * \
                np.exp(-seq / 950)

        def write_voice(dest, samples):
            with wave.open(str(dest), 'wb') as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(sample_rate)
                w.writeframes((np.clip(samples, -1, 1) * 32767).
                              astype('<i2').tobytes())

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            work = root / 'work'
            dist = root / 'dist'
            work.mkdir()
            write_voice(work / 'voice.mp3', signal)  # PCM content, FFmpeg detects it.
            write_voice(work / 'music.wav', .05 * np.sin(2 * np.pi * 110 * t))
            write_voice(work / 'effects.wav', np.zeros(count))
            subprocess.run(
                ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                 '-f', 'lavfi', '-i',
                 f'color=c=black:s=120x212:r=30:d={length}',
                 '-c:v', 'mpeg4', str(work / 'silent.mp4')],
                check=True)
            with patch.object(pipeline, 'WORK', work), \
                    patch.object(pipeline, 'DIST', dist), \
                    patch.object(pipeline, 'audio_files'):
                pipeline.master()
            final = dist / 'video.mp4'
            self.assertTrue(final.is_file())
            self.assertLessEqual(pipeline.measured_true_peak(final), -1.5)
            self.assertTrue(-16 <= pipeline.measured_lufs(final) <= -12)
            self.assertIn('alimiter=limit=0.620', pipeline.master_graph())

    def test_peak_overshoot_triggers_fresh_second_mix(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(pipeline, 'WORK', Path(temp)), \
                    patch.object(pipeline, 'DIST', Path(temp)), \
                    patch.object(pipeline, 'audio_files'), \
                    patch.object(pipeline.subprocess, 'run') as run, \
                    patch.object(pipeline, 'measured_true_peak',
                                 side_effect=[-1.0, -2.8]), \
                    patch.object(pipeline, 'measured_lufs',
                                 side_effect=[-15.5, -15.5]):
                pipeline.master()
                self.assertEqual(run.call_count, 2)
                self.assertIn('alimiter=limit=0.620',
                              run.call_args_list[0].args[0][
                                  run.call_args_list[0].args[0].index('-filter_complex') + 1])
                self.assertIn('alimiter=limit=0.480',
                              run.call_args_list[1].args[0][
                                  run.call_args_list[1].args[0].index('-filter_complex') + 1])

    def test_low_lufs_gets_automatic_second_mix(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(pipeline, 'WORK', Path(temp)), \
                    patch.object(pipeline, 'DIST', Path(temp)), \
                    patch.object(pipeline, 'audio_files'), \
                    patch.object(pipeline.subprocess, 'run') as run, \
                    patch.object(pipeline, 'measured_true_peak', side_effect=[-4.06, -3.0]), \
                    patch.object(pipeline, 'measured_lufs', side_effect=[-16.8, -14.9]):
                pipeline.master()
                self.assertEqual(run.call_count, 2)
                self.assertIn('volume=+2.00dB', str(run.call_args_list[1]))

    def test_invalid_post_aac_loudness_still_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(pipeline, 'WORK', Path(temp)), \
                    patch.object(pipeline, 'DIST', Path(temp)), \
                    patch.object(pipeline, 'audio_files'), \
                    patch.object(pipeline.subprocess, 'run'), \
                    patch.object(pipeline, 'measured_true_peak',
                                 return_value=-3.0), \
                    patch.object(pipeline, 'measured_lufs',
                                 return_value=-17.0):
                with self.assertRaisesRegex(RuntimeError, 'volumen y true peak'):
                    pipeline.master()


if __name__ == '__main__':
    unittest.main()
