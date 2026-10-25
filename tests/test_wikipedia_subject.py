import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pipeline
from topic_research import candidate_selection, gather_candidates, topic_plan


EXTRACT = (
    'La bioluminiscencia es la producción de luz por organismos vivos. '
    'Algunos animales marinos generan destellos mediante reacciones químicas. '
    'El plancton marino puede producir luz visible durante la noche. '
    'El fenómeno ocurre en una variedad de organismos del océano. '
    'La emisión de luz puede intervenir en la comunicación y la defensa.'
)


class FakeGemini:
    def __init__(self, selection='A1'):
        self.selection = selection

    def generate(self, prompt, temperature=0, **kwargs):
        if prompt.startswith('Planea SOLO'):
            return {
                'focus': 'Bioluminiscencia',
                'queries_es': ['bioluminiscencia marina'],
                'queries_en': [],
                'anchors': ['bioluminiscencia', 'mar', 'luz'],
                'visual_exclusions': ['luces artificiales']
            }
        if prompt.startswith('Filtra resultados'):
            return {'selected': [self.selection] if self.selection else []}
        raise AssertionError('Unexpected Gemini call')


class GeneralWikipediaResearchTests(unittest.TestCase):
    def fake_wiki(self, params, commons=False, lang='es'):
        if params.get('list') == 'search':
            return {'query': {'search': [
                {'title': 'Bioluminiscencia',
                 'snippet': 'Producción de luz por organismos marinos.'},
                {'title': 'El Cerrejón',
                 'snippet': 'Explotación de carbón de Colombia.'}]}}
        if params.get('prop') == 'extracts':
            return {'query': {'pages': [
                {'title': params['titles'], 'extract': EXTRACT}]}}
        raise AssertionError('Unexpected Wikimedia request')

    def test_question_maps_to_relevant_article_without_exact_name(self):
        topic = '¿Por qué brilla el mar de noche?'
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(pipeline, 'mediawiki', side_effect=self.fake_wiki), \
                    patch.object(pipeline, 'Gemini', return_value=FakeGemini()), \
                    patch.object(pipeline, 'WORK', Path(directory)):
                facts, sources = pipeline.wikipedia(topic)
                plan = pipeline.load_json(Path(directory) / 'topic_plan.json')
        self.assertGreaterEqual(len(facts), 4)
        self.assertEqual(sources[0]['title'], 'Bioluminiscencia')
        self.assertEqual(plan['topic'], topic)
        self.assertEqual(plan['selected_articles'][0]['title'], 'Bioluminiscencia')

    def test_no_relevant_article_fails_closed(self):
        with patch.object(pipeline, 'mediawiki', side_effect=self.fake_wiki), \
                patch.object(pipeline, 'Gemini', return_value=FakeGemini(selection='')):
            with self.assertRaisesRegex(RuntimeError, 'Ningún artículo'):
                pipeline.wikipedia('Tema sin fuentes')

    def test_candidate_filter_cannot_invent_articles(self):
        cat = [{'id': 'A1', 'lang': 'es', 'title': 'Bioluminiscencia',
                'snippet': 'Luz producida por seres vivos.'}]
        gm = FakeGemini(selection='A999')
        plan = {'focus': 'Bioluminiscencia'}
        self.assertEqual(candidate_selection('Bioluminiscencia', plan, cat, gm), [])

    def test_search_result_ranking_removes_duplicates(self):
        plan = {'focus': 'Bioluminiscencia',
                'queries_es': ['bioluminiscencia marina'],
                'queries_en': []}
        cat = gather_candidates('Luz del mar', plan, self.fake_wiki)
        self.assertEqual([item['title'] for item in cat],
                         ['Bioluminiscencia', 'El Cerrejón'])


if __name__ == '__main__':
    unittest.main()
