import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from offline_voice import estimate_wordmarks, narration, words_in


class OfflineVoiceTests(TestCase):
    def test_spanish_tokenization_and_word_order(self):
        self.assertEqual(words_in('¡Hola, Titán! ¿Dónde vivió?'),
                         ['Hola', 'Titán', 'Dónde', 'vivió'])
        scenes = [{'line': 'La serpiente gigante'},
                  {'line': '¿Qué opinas de esto?'}]
        marks = estimate_wordmarks(scenes, [(0, 2.5), (2.65, 4.9)])
        self.assertEqual([m['text'] for m in marks],
                         ['La', 'serpiente', 'gigante', 'Qué', 'opinas', 'de', 'esto'])
        self.assertAlmostEqual(marks[0]['start'], 0, places=3)
        self.assertAlmostEqual(marks[-1]['end'], 4.9, places=3)
        self.assertTrue(all(0 <= m['start'] < m['end'] for m in marks))

    def test_fallback_and_mp3_length_without_remote_tts(self):
        scenes = [{'line': 'Este es un ejemplo breve de audio seguro.'}
                  for _ in range(12)]
        def fake_segments(scenes, directory, engine, voice=None):
            self.assertEqual(engine, 'eSpeak NG')
            return [(22050, b'\x00\x00' * (22050 * 3)) for _ in scenes]

        with tempfile.TemporaryDirectory() as tempdir:
            with patch('offline_voice.piper_engine',
                       side_effect=RuntimeError('No voice model')):
                with patch('offline_voice.write_scene_audio',
                           side_effect=fake_segments):
                    marks, length, engine = narration(
                        scenes, Path(tempdir) / 'voice.mp3')
            self.assertEqual(engine, 'eSpeak NG')
            self.assertTrue(30 <= length <= 45)
            self.assertEqual(len(marks), sum(len(words_in(s['line']))
                                             for s in scenes))
            self.assertTrue((Path(tempdir) / 'voice.mp3').stat().st_size > 500)

    def test_fails_on_scene_without_words(self):
        with self.assertRaises(RuntimeError):
            estimate_wordmarks([{'line': '!!!'}], [(0, 1)])
