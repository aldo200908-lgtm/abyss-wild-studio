import unittest

from topic_guard import topic_problems


class TopicFocusTests(unittest.TestCase):
    def test_rejects_cerrejon_coal_script_requested_titanoboa(self):
        lines = [
            'La formación Cerrejón data del Paleoceno',
            'Esta se halla en la Guajira',
            'La formación consiste de campos de hulla',
            'Constituyen un importante recurso económico',
            'El carbón ha sido explotado intensivamente',
            'Es una de las mayores del mundo',
            'Posee fósiles de selvas neotropicales',
            'Son los primeros registros conocidos',
            'La formación se subdivide en tres grupos',
            'Esto se basa en los lechos de carbón',
            'En promedio los lechos miden tres metros',
            'Alcanzan hasta diez metros de grosor',
            '¿Conocías estos datos sobre el Cerrejón?',
        ]
        issues = topic_problems('Titanoboa', [{'line': s} for s in lines],
                                title='Cerrejón')
        self.assertTrue(issues)
        self.assertTrue(any('carbón' in issue for issue in issues))

    def test_accepts_giant_snake_subject(self):
        lines = [
            'Titanoboa podía medir casi trece metros',
            'Esta serpiente fue gigantesca',
            'Sus fósiles se encontraron en Colombia',
            'Vivió en selvas de hace millones de años',
            'Titanoboa dejó vértebras descomunales',
            'Sus huesos permiten estimar la longitud',
            'La serpiente tenía un cuerpo colosal',
            'Sus fósiles muestran un depredador grande',
            'El tamaño superaba a serpientes actuales',
            'Sus presas incluían fauna de aquella selva',
            'Un reptil enorme del Paleoceno',
            'La gigante Titanoboa inspira investigaciones',
            '¿Te imaginarías encontrarte con Titanoboa?',
        ]
        self.assertEqual(
            topic_problems('Titanoboa', [{'line': s} for s in lines],
                           title='Titanoboa: serpiente gigante'), [])

    def test_rejects_missing_topic_in_opening_and_final_question(self):
        scenes = [{'line': 'Otro hecho sin mencionar al sujeto'} for _ in range(13)]
        scenes[-1] = {'line': '¿Qué opinas de esto?'}
        issues = topic_problems('Titanoboa', scenes, title='Titanoboa')
        self.assertTrue(any('gancho' in issue for issue in issues))
        self.assertTrue(any('pregunta' in issue for issue in issues))


if __name__ == '__main__':
    unittest.main()
