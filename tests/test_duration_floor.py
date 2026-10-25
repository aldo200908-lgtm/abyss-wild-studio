"""Short #15 duration-floor regression after silence-trimmed Azure Speech.

The natural Jorge recording may be 29.9s. Keep voice byte timing untouched,
place a <=350ms visual/music-only outro, and never add gaps between phrases.
"""
import math
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np

import pipeline
from narration_budget import video_duration_for_narration
from native_spanish_voice import (
    NarrationDurationError, render_native_voice,
)
from tests.test_narration_budget import example_scenes, VOICE_CONFIG


class VideoDurationPlanTests(unittest.TestCase):
    def test_short_15_29_9_is_padded_visually_not_vocally(self):
        self.assertEqual(video_duration_for_narration(29.9), 30.1)
        self.assertAlmostEqual(video_duration_for_narration(29.9)-29.9, .2)

    def test_safe_near_floor_and_normal_durations(self):
        for voice_duration in (29.75, 29.9, 30, 30.15, 37, 44.95, 45):
            with self.subTest(voice_duration=voice_duration):
                planned=video_duration_for_narration(voice_duration)
                self.assertGreaterEqual(planned,30.1)
                self.assertLessEqual(planned,45)
                self.assertGreaterEqual(planned,voice_duration)
                self.assertLessEqual(planned-voice_duration,.35+1e-7)

    def test_truly_short_or_overlong_voice_cannot_be_padded(self):
        for seconds in (0, 25, 29.5, 29.74, 45.1, 48, 52.4):
            with self.subTest(seconds=seconds):
                with self.assertRaises(ValueError):
                    video_duration_for_narration(seconds)

    def test_timeline_uses_real_word_offsets_but_full_visual_outro(self):
        class FakeAzure:
            def __init__(self,key,region):
                pass
            def ensure_voice(self,voice):
                pass
        script={'topic':'Titanoboa','title':'Titanoboa',
                'scenes':example_scenes()}
        ws=[word for sc in script['scenes'] for word in pipeline.tokens(sc['line'])]
        voice_seconds=29.9
        marks=[{'text':word,
                'start':round(i*voice_seconds/len(ws),3),
                'end':round((i+1)*voice_seconds/len(ws),3)}
               for i,word in enumerate(ws)]
        voice_meta={'voice':'es-MX-JorgeNeural','locale':'es-MX',
                    'pauses':[],'normalized_text':' '.join(ws)}
        with tempfile.TemporaryDirectory() as directory:
            work=Path(directory)/'work'
            dist=Path(directory)/'dist'
            with patch.object(pipeline,'WORK',work), \
                 patch.object(pipeline,'DIST',dist), \
                 patch.object(pipeline,'config_from',return_value=VOICE_CONFIG), \
                 patch.object(pipeline,'load_dictionary',return_value={}), \
                 patch.object(pipeline,'AzureSpanishSpeech',FakeAzure), \
                 patch.object(pipeline,'render_native_voice',
                              return_value=(marks,voice_seconds,voice_meta)), \
                 patch.object(pipeline,'whisper_quality',
                              return_value={'transcription_match':.95}):
                pipeline.make_timing(script)
            doc=pipeline.load_json(work/'script.json')
            meta=pipeline.load_json(work/'voice_meta.json')
            self.assertEqual(doc['duration'],30.1)
            self.assertEqual(doc['voice_duration'],29.9)
            self.assertAlmostEqual(doc['ambient_outro_seconds'],.2)
            self.assertAlmostEqual(doc['timeline'][-1]['end'],30.1)
            self.assertLessEqual(doc['captions'][-1]['end'],29.9)
            self.assertEqual(meta['pauses'],[])
            self.assertAlmostEqual(meta['ambient_outro_seconds'],.2)


class NaturallyTimedAzureTest(unittest.TestCase):
    def test_near_floor_pcm_is_kept_at_original_tts_speed(self):
        class FakeAzure:
            def __init__(self):
                self.calls=0
            def synthesize(self,text,target,voice,rate):
                self.calls+=1
                self.assert_settings=(voice,rate)
                frequency=24000
                n=round(frequency*5.98)
                t=np.arange(n,dtype=np.float32)/frequency
                samples=(.23*np.sin(2*np.pi*230*t)*32767).astype('<i2')
                with wave.open(str(target),'wb') as out:
                    out.setnchannels(1)
                    out.setsampwidth(2)
                    out.setframerate(frequency)
                    out.writeframes(samples.tobytes())
        scene={'line':'Titanoboa fue una enorme serpiente de antiguas selvas colombianas.'}
        from spanish_voice_text import load_dictionary
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'voice.mp3'
            fake=FakeAzure()
            marks,seconds,meta=render_native_voice(
                [dict(scene) for i in range(10)],output,
                {'voice':'es-MX-JorgeNeural','rate_percent':-2,
                 'phrase_min_words':8,'phrase_max_words':18},
                load_dictionary(Path(__file__).resolve().parents[1]/
                                'pronunciacion.json'),
                fake)
            self.assertGreaterEqual(seconds,29.75)
            self.assertLess(seconds,30.0)
            self.assertEqual(meta['pauses'],[])
            self.assertEqual(fake.assert_settings,('es-MX-JorgeNeural',-2))
            self.assertEqual(fake.calls,5)
            self.assertEqual(len(marks),90)
            self.assertTrue(output.stat().st_size>1000)


if __name__=='__main__':
    unittest.main()
