import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from native_spanish_voice import (VOICES, config_from, validate_locale,
                                  transcript_score, wordmarks_per_scene)
from spanish_voice_text import (normalizar, fonetizar, load_dictionary,
                                grupos_de_frases)


CONFIG = {
    'voice': 'es-PE-AlexNeural', 'tts_provider': 'azure',
    'rate_percent': -2, 'phrase_min_words': 8, 'phrase_max_words': 18,
    'pause_min_seconds': .2, 'pause_max_seconds': .5,
    'whisper_language': 'es', 'whisper_model': 'small',
    'min_transcription_match': .92,
    'verify_voice_locale': True, 'strict_no_fallback': True,
}


class NativeVoiceUnitTests(unittest.TestCase):
    def test_all_five_ids_are_spanish(self):
        self.assertEqual(len(VOICES), 5)
        self.assertTrue(all(s.startswith('es-') for s in VOICES))
        self.assertTrue(all('Multilingual' not in s for s in VOICES))

    def test_config_rejects_foreign_or_multilingual_voice(self):
        for voice in ('en-US-AvaMultilingualNeural',
                      'es-MX-JorgeMultilingualNeural',
                      'en-US-GuyNeural', 'es-MX-ImaginaryNeural'):
            with tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / 'config.json'
                p.write_text(json.dumps({**CONFIG, 'voice': voice}))
                with self.assertRaises(ValueError):
                    config_from(p)

    def test_config_accepts_native_voice(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'config.json'
            p.write_text(json.dumps(CONFIG))
            self.assertEqual(config_from(p)['voice'], 'es-PE-AlexNeural')

    def test_wrong_locale_rejected_before_synthesis(self):
        voice = SimpleNamespace(short_name='es-PE-AlexNeural', locale='en-US')
        with self.assertRaisesRegex(RuntimeError, 'Locale inválido'):
            validate_locale('es-PE-AlexNeural', [voice])

    def test_locale_matches_voice_language_and_region(self):
        voice = SimpleNamespace(short_name='es-PE-AlexNeural', locale='es-PE')
        self.assertEqual(validate_locale('es-PE-AlexNeural', [voice]), 'es-PE')
        with self.assertRaisesRegex(RuntimeError, 'Locale no coincide'):
            validate_locale('es-PE-AlexNeural',
                            [SimpleNamespace(short_name='es-PE-AlexNeural',
                                             locale='es-MX')])

    def test_no_silent_missing_azure_credentials(self):
        from native_spanish_voice import AzureSpanishSpeech
        with self.assertRaisesRegex(RuntimeError, 'Faltan Secrets'):
            AzureSpanishSpeech('', '')

    def test_range_kilos_percent_date(self):
        self.assertIn('doce a catorce metros', normalizar('12-14 m'))
        self.assertIn('mil ciento treinta y cinco kilos', normalizar('1.135 kg'))
        self.assertIn('por ciento', normalizar('25%'))
        self.assertIn('de octubre de dos mil veintiséis',
                      normalizar('24/10/2026'))

    def test_spanish_o_u_grammar(self):
        self.assertEqual(normalizar('doce u catorce'), 'doce o catorce')
        self.assertEqual(normalizar('siete o ocho'), 'siete u ocho')
        self.assertEqual(normalizar('siete u hojas'), 'siete u hojas')

    def test_no_unexplained_acronyms(self):
        with self.assertRaisesRegex(ValueError, 'Siglas'):
            normalizar('Los fósiles llegaron a XYZ')

    def test_dictionary_has_thirty_entries(self):
        root = Path(__file__).resolve().parents[1]
        dic = load_dictionary(root / 'pronunciacion.json')
        self.assertEqual(len(dic), 30)
        self.assertIn('titanobóa', fonetizar('Titanoboa', dic))
        self.assertEqual(fonetizar('Una hermosa serpiente', dic),
                         'Una hermosa serpiente')

    def test_8_18_word_phrases(self):
        scenes = [
            'La serpiente prehistórica habitó un paisaje tropical muy húmedo',
            'Los científicos estudiaron fósiles encontrados en la región colombiana',
            'Cada vértebra ofrece pistas importantes sobre el tamaño corporal',
        ]
        groups = grupos_de_frases(scenes, 8, 18)
        self.assertTrue(groups)
        self.assertTrue(all(8 <= sum(len(x.split()) for _, x in g) <= 18
                            for g in groups))

    def test_word_timing_remains_ordered(self):
        scenes = [{'line': 'Titanoboa fue una enorme serpiente'},
                  {'line': 'Su tamaño impresionó a investigadores'}]
        marks = wordmarks_per_scene(scenes, [(0, 3.1), (3.3, 6.1)])
        self.assertTrue(all(marks[i]['start'] <= marks[i+1]['start']
                            for i in range(len(marks)-1)))

    def test_whisper_92_percent_threshold(self):
        good, _ = transcript_score('uno dos tres cuatro cinco seis siete ocho '
                                   'nueve diez once doce trece',
                                   'uno dos tres cuatro cinco seis siete ocho '
                                   'nueve diez once doce trece')
        bad, suspects = transcript_score('titanoboa era serpiente muy gigante',
                                         'el carbón era importante')
        self.assertEqual(good, 1.0)
        self.assertLess(bad, .92)
        self.assertTrue(suspects)


if __name__ == '__main__':
    unittest.main()
