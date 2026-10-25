import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline


class WikipediaSubjectTests(unittest.TestCase):
    def test_only_exact_title_article_is_accepted(self):
        extract = (
            'Titanoboa fue una serpiente prehistórica de gran tamaño en Colombia. '
            'Se conocen vértebras fósiles que permitieron calcular su longitud. '
            'Los ejemplares existieron en el Paleoceno en una región selvática. '
            'Las investigaciones de fósiles permiten comparar el tamaño de estos reptiles. '
            'Titanoboa es conocida por alcanzar un tamaño muy superior al de numerosas serpientes.'
        )
        def fake_api(parameters, commons=False):
            self.assertEqual(parameters.get('titles'), 'Titanoboa')
            return {'query': {'pages': [{'title': 'Titanoboa', 'extract': extract}]}}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(pipeline, 'mediawiki', side_effect=fake_api), \
                    patch.object(pipeline, 'WORK', Path(directory)):
                facts, sources = pipeline.wikipedia('Titanoboa')
        self.assertGreaterEqual(len(facts), 4)
        self.assertEqual(sources[0]['title'], 'Titanoboa')

    def test_related_search_results_cannot_replace_requested_topic(self):
        calls = []
        def fake_api(parameters, commons=False):
            calls.append(parameters)
            if 'prop' in parameters:
                return {'query': {'pages': [{'title': 'Formación Cerrejón',
                                             'extract': 'Texto sobre la minería del carbón.'}]}}
            return {'query': {'search': [{'title': 'Formación Cerrejón'}]}}
        with patch.object(pipeline, 'mediawiki', side_effect=fake_api):
            with self.assertRaisesRegex(RuntimeError, 'artículo cuyo título coincida'):
                pipeline.wikipedia('Titanoboa')
        self.assertEqual(len(calls), 2)


if __name__ == '__main__':
    unittest.main()
