import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from script_repair import apply_scene_repairs
from topic_guard import topic_problems
import pipeline


def sample_scenes():
    scenes = [
        {'line': 'Titanoboa era una serpiente enorme de Colombia.',
         'fact_ids': ['F1'], 'visual_type': 'infographic'}
    ]
    scenes += [
        {'line': 'Aquella especie habitó regiones cálidas hace mucho tiempo.',
         'fact_ids': ['F1'], 'visual_type': 'infographic'}
        for _ in range(11)
    ]
    scenes.append({'line': '¿Te imaginas ver una Titanoboa en persona?',
                   'fact_ids': [], 'visual_type': 'infographic'})
    return scenes


class RepairTests(unittest.TestCase):
    def test_lexical_gate_does_not_demand_repetition_every_scene(self):
        issues = topic_problems('Titanoboa', sample_scenes(),
                                title='Titanoboa gigante', anchors=['serpiente'])
        self.assertEqual(issues, [])

    def test_repair_only_target_scene(self):
        scenes = sample_scenes()
        proposal = {'replacements': [
            {'index': 8,
             'line': 'Sus fósiles permiten investigar sus enormes dimensiones.',
             'fact_ids': ['F2'], 'visual_type': 'fossil',
             'visual_query': 'Titanoboa fossil vertebra'}
        ]}
        amended = apply_scene_repairs(scenes, proposal, [8], {'F1', 'F2'})
        self.assertIsNotNone(amended)
        self.assertEqual(amended[8]['fact_ids'], ['F2'])
        self.assertEqual(amended[8]['visual_type'], 'fossil')
        self.assertEqual(amended[-1], scenes[-1])
        self.assertEqual(scenes[8]['fact_ids'], ['F1'])
        for i in range(len(scenes)):
            if i != 8:
                self.assertEqual(amended[i], scenes[i])

    def test_repair_rejects_unsupported_or_wrong_indices(self):
        scenes = sample_scenes()
        baseline = {'index': 8, 'line': 'Sus fósiles permiten investigar sus enormes dimensiones.',
                    'fact_ids': ['F2']}
        for item in ({**baseline, 'index': 9},
                     {**baseline, 'fact_ids': ['FABRICATED']},
                     {**baseline, 'line': scenes[8]['line']},
                     {**baseline, 'line': 'Uno'},
                     {**baseline, 'index': 12}):
            self.assertIsNone(apply_scene_repairs(
                scenes, {'replacements': [item]}, [8], {'F1', 'F2'}))

    def test_missing_partial_repair_is_rejected(self):
        scenes = sample_scenes()
        self.assertIsNone(apply_scene_repairs(
            scenes, {'replacements': [{'index': 8,
                                       'line': 'Una serpiente gigantesca vivió durante el Paleoceno.',
                                       'fact_ids': ['F1']}]},
            [7, 8], {'F1'}))

    def test_rejected_scene_is_reaudited_after_repair(self):
        class MockGemini:
            def __init__(self):
                self.audits = 0
                self.repairs = 0

            def generate(self, prompt, temperature=0.2, **kwargs):
                if prompt.startswith('Crea un único YouTube Short'):
                    return {'title': 'Titanoboa gigante',
                            'scenes': sample_scenes()}
                if prompt.startswith('Eres auditor factual'):
                    self.audits += 1
                    return {'rejected': [8] if self.audits == 1 else [],
                            'focus_ok': True}
                if prompt.startswith('Corrige EXCLUSIVAMENTE'):
                    self.repairs += 1
                    return {'replacements': [
                        {'index': 8, 'line': 'Sus fósiles revelan pistas de sus dimensiones.',
                         'fact_ids': ['F2'], 'visual_type': 'fossil'}]}
                raise AssertionError('Unexpected API call: ' + prompt[:55])
        mock = MockGemini()
        facts = [
            {'id': 'F1', 'text': 'Titanoboa era una serpiente prehistórica de Colombia '
             'que vivió en regiones cálidas durante el Paleoceno.',
             'url': 'https://es.wikipedia.org/wiki/Titanoboa'},
            {'id': 'F2', 'text': 'Los restos fósiles de Titanoboa proporcionan información '
             'sobre sus dimensiones.',
             'url': 'https://es.wikipedia.org/wiki/Titanoboa'}
        ]
        plan = {'focus': 'Titanoboa', 'anchors': ['serpiente', 'fósiles'],
                'visual_exclusions': []}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(pipeline, 'WORK', Path(directory)), \
                    patch.object(pipeline, 'Gemini', return_value=mock):
                pipeline.save_json(Path(directory) / 'topic_plan.json', plan)
                result = pipeline.create_script(
                    'Titanoboa', facts, [{'title': 'Titanoboa',
                                          'url': facts[0]['url']}])
                self.assertEqual(result['scenes'][8]['fact_ids'], ['F2'])
                self.assertEqual(mock.repairs, 1)
                self.assertEqual(mock.audits, 2)
                self.assertTrue((Path(directory) / 'script.json').is_file())

    def test_audit_does_not_approve_off_topic(self):
        class NoFocusGemini:
            calls = 0

            def generate(self, prompt, **kwargs):
                if prompt.startswith('Crea un único YouTube Short'):
                    self.calls += 1
                    return {'title': 'Titanoboa gigante',
                            'scenes': sample_scenes()}
                if prompt.startswith('Eres auditor factual'):
                    return {'rejected': [], 'focus_ok': False}
                raise AssertionError('Should not attempt a repair when focus is invalid')
        mock = NoFocusGemini()
        plan = {'focus': 'Titanoboa', 'anchors': ['serpiente'],
                'visual_exclusions': []}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(pipeline, 'WORK', Path(directory)), \
                    patch.object(pipeline, 'Gemini', return_value=mock):
                pipeline.save_json(Path(directory) / 'topic_plan.json', plan)
                with self.assertRaisesRegex(RuntimeError, 'Sin guion'):
                    pipeline.create_script('Titanoboa',
                                           [{'id': 'F1', 'text': 'Hecho verificable',
                                             'url': 'https://es.wikipedia.org/wiki/Titanoboa'}],
                                           [{'title': 'Titanoboa', 'url': 'example'}])
        self.assertEqual(mock.calls, 3)


if __name__ == '__main__':
    unittest.main()
