import unittest

from response_shapes import normalize_audit_payload, normalize_script_payload


class GeminiResponseTests(unittest.TestCase):
    def setUp(self):
        self.scenes = [
            {'line': 'Frase verificable', 'fact_ids': ['F1'],
             'visual_type': 'infographic'} for _ in range(12)
        ]
        self.scenes.append({'line': '¿Qué te parece?', 'fact_ids': []})

    def test_object_shape(self):
        value = normalize_script_payload(
            {'title': 'Titanoboa', 'scenes': self.scenes}, 'Titanoboa')
        self.assertEqual(len(value['scenes']), 13)

    def test_scene_list_shape(self):
        value = normalize_script_payload(self.scenes, 'Titanoboa')
        self.assertEqual(value['title'], 'Titanoboa')
        self.assertEqual(value['scenes'][0]['fact_ids'], ['F1'])

    def test_single_object_list_shape(self):
        value = normalize_script_payload(
            [{'title': 'Titanoboa', 'scenes': self.scenes}], 'Titanoboa')
        self.assertEqual(len(value['scenes']), 13)

    def test_nested_script_shape(self):
        value = normalize_script_payload(
            {'result': {'scenes': self.scenes}}, 'Titanoboa')
        self.assertEqual(len(value['scenes']), 13)

    def test_malformed_script_is_rejected(self):
        for value in ([1, 2], 'text', {}, [{'scenes': 'bad'}], []):
            self.assertIsNone(normalize_script_payload(value, 'Titanoboa'))
        bad_scenes = [dict(scene) for scene in self.scenes]
        bad_scenes[1]['fact_ids'] = 'F1'
        self.assertIsNone(normalize_script_payload(bad_scenes, 'Titanoboa'))

    def test_audit_object(self):
        self.assertEqual(normalize_audit_payload(
            {'rejected': [2, 1, 2]}, 12), [1, 2])
        self.assertEqual(normalize_audit_payload(
            [{'rejected': []}], 12), [])

    def test_audit_list(self):
        self.assertEqual(normalize_audit_payload([3, 0], 12), [0, 3])

    def test_audit_unknown_shape_fails_closed(self):
        for value in ({}, {'rejected': 'none'}, ['pass'], [False], [12],
                      {'rejected': [-1]}, {'rejected': [12]}):
            self.assertIsNone(normalize_audit_payload(value, 12))


if __name__ == '__main__':
    unittest.main()
