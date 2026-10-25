"""Titanoboa demonstration: native Spanish voice, no cloud secrets needed."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from native_spanish_voice import config_from, validate_locale, VOICES
from spanish_voice_text import normalizar, fonetizar, load_dictionary, grupos_de_frases


class TitanoboaNarrationCase(unittest.TestCase):
    def test_numerical_phrasing_and_place_names(self):
        source = ('Titanoboa cerrejonensis medía entre 12-14 m. '
                  'Su masa podía alcanzar 1.135 kg en esta frase de prueba.')
        rendered = normalizar(source)
        self.assertIn('doce a catorce metros', rendered)
        self.assertIn('mil ciento treinta y cinco kilos', rendered)
        dictionary = load_dictionary(
            Path(__file__).resolve().parents[1] / 'pronunciacion.json')
        spoken = fonetizar(rendered, dictionary)
        self.assertIn('titanobóa serrejonénsis', spoken)
        self.assertNotIn('12-14', spoken)
        self.assertNotIn('1.135', spoken)

    def test_native_peruvian_voice_verified_by_locale(self):
        root = Path(__file__).resolve().parents[1]
        config = config_from(root / 'config.json')
        self.assertIn(config['voice'], VOICES)
        voices = [SimpleNamespace(short_name=config['voice'],
                                  locale=config['voice'][:5])]
        self.assertEqual(validate_locale(config['voice'], voices), config['voice'][:5])

    def test_spanish_o_before_consonant(self):
        self.assertEqual(normalizar('doce u catorce metros'),
                         'doce o catorce metros')

    def test_short_lesson_is_phrasable(self):
        phrases = [
            'Titanoboa fue una serpiente gigante de antiguas selvas americanas',
            'Su estudio comenzó con importantes descubrimientos fósiles en Colombia',
            'Investigadores analizaron vértebras y reconstruyeron dimensiones del animal',
        ]
        groups = grupos_de_frases(phrases, 8, 18)
        self.assertGreaterEqual(len(groups), 2)
        self.assertEqual([idx for group in groups for idx, _ in group], [0, 1, 2])
        self.assertTrue(all(8 <= sum(len(t.split()) for _, t in group) <= 18
                            for group in groups))


if __name__ == '__main__':
    unittest.main()
