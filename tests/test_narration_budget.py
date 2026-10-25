"""Tests for Jorge's measured narration runtime and safe overlength recovery."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline
from narration_budget import (predict_duration, spoken_word_count,
                              remove_secondary_scene)
from native_spanish_voice import NarrationDurationError

VOICE_CONFIG = {
    'voice': 'es-MX-JorgeNeural',
    'phrase_min_words': 8, 'phrase_max_words': 18,
    'pause_min_seconds': 0.2, 'pause_max_seconds': 0.5,
}


def example_scenes():
    scenes = [
        {'line': 'Titanoboa habitó las selvas tropicales de la antigua Colombia.',
         'fact_ids': ['F1']}
    ]
    scenes += [
        {'line': 'Aquella serpiente tenía dimensiones enormes en Colombia.',
         'fact_ids': ['F1']}
        for _ in range(8)
    ]
    scenes.append({'line': '¿Te imaginas encontrarte con una Titanoboa en persona?',
                   'fact_ids': []})
    return scenes


class NarrationBudgetTests(unittest.TestCase):
    def test_october_overlong_script_cannot_pass_preflight(self):
        big = example_scenes() + [
            {'line': 'Muchos fósiles todavía ofrecen pistas sobre animales antiguos.',
             'fact_ids': ['F1']} for _ in range(3)
        ]
        estimate = predict_duration(big, VOICE_CONFIG)
        self.assertGreater(estimate, 45)

    def test_valid_script_uses_natural_voice_without_speed_up(self):
        scenes = example_scenes()
        self.assertEqual(len(scenes), 10)
        self.assertTrue(30 < predict_duration(scenes, VOICE_CONFIG) < 44)
        self.assertGreaterEqual(spoken_word_count(scenes), 65)

    def test_prunes_middle_without_new_facts(self):
        scenes = example_scenes()
        shortened = remove_secondary_scene(scenes, VOICE_CONFIG)
        self.assertIsNotNone(shortened)
        revised, index, cut = shortened
        self.assertGreaterEqual(index, 2)
        self.assertLess(index, len(scenes) - 2)
        self.assertEqual(len(revised), 9)
        self.assertEqual(revised[0], scenes[0])
        self.assertEqual(revised[-1], scenes[-1])
        self.assertIn(cut, scenes)
        self.assertEqual(len(scenes), 10)

    def test_too_few_scenes_does_not_remove_anything(self):
        self.assertIsNone(remove_secondary_scene(example_scenes()[:8], VOICE_CONFIG))

    def test_audio_52_seconds_retries_with_verified_shorter_script(self):
        class FakeAzure:
            def __init__(self, key, region):
                self.key = key
            def ensure_voice(self, voice):
                self.voice = voice
        calls = []
        def fake_voice(scenes, dest, settings, dictionary, speaker):
            calls.append(len(scenes))
            if len(calls) == 1:
                raise NarrationDurationError(52.4)
            duration = 40.0
            ws = [w for sc in scenes for w in pipeline.tokens(sc['line'])]
            marks = [
                {'text': w, 'start': round(i * duration / len(ws), 3),
                 'end': round((i+1) * duration / len(ws), 3)}
                for i, w in enumerate(ws)
            ]
            return marks, duration, {'voice': 'es-MX-JorgeNeural',
                                     'pauses': [0.3] * 4,
                                     'normalized_text': ' '.join(ws)}
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory) / 'work'
            dist = Path(directory) / 'dist'
            script = {'topic': 'Titanoboa', 'title': 'Titanoboa',
                      'topic_plan': {'anchors': ['Titanoboa', 'serpiente']},
                      'scenes': example_scenes()}
            with patch.object(pipeline, 'WORK', work), \
                    patch.object(pipeline, 'DIST', dist), \
                    patch.object(pipeline, 'config_from', return_value=VOICE_CONFIG), \
                    patch.object(pipeline, 'load_dictionary', return_value={}), \
                    patch.object(pipeline, 'AzureSpanishSpeech', FakeAzure), \
                    patch.object(pipeline, 'render_native_voice',
                                 side_effect=fake_voice), \
                    patch.object(pipeline, 'whisper_quality',
                                 return_value={'transcription_match': .99}):
                pipeline.make_timing(script)
                saved = pipeline.load_json(work / 'script.json')
            self.assertEqual(calls, [10, 9])
            self.assertEqual(len(saved['scenes']), 9)
            self.assertEqual(len(saved['removed_voice_budget_scenes']), 1)
            self.assertEqual(len(saved['timeline']), 9)
            self.assertTrue(30 <= saved['duration'] <= 45)
            self.assertTrue(all(len(c['words']) == 1 for c in saved['captions']))


if __name__ == '__main__':
    unittest.main()
