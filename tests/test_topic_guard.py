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
        self.assertTrue(any('gancho' in issue or 'conceptos centrales' in issue for issue in issues))

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
                           title='Titanoboa: serpiente gigante',
                           anchors=['serpiente', 'fósiles', 'reptil', 'gigante']), [])

    def test_rejects_missing_topic_in_opening_and_final_question(self):
        scenes = [{'line': 'Otro hecho sin mencionar al sujeto'} for _ in range(13)]
        scenes[-1] = {'line': '¿Qué opinas de esto?'}
        issues = topic_problems('Titanoboa', scenes, title='Titanoboa')
        self.assertTrue(any('gancho' in issue for issue in issues))
        self.assertTrue(any('pregunta' in issue for issue in issues))


if __name__ == '__main__':
    unittest.main()

    def test_question_topic_can_use_synonym_instead_of_exact_phrase(self):
        lines = [
            'El mar puede brillar durante la noche',
            'La bioluminiscencia produce esta luz',
            'Muchos organismos generan destellos',
            'La luminosidad cambia con el movimiento',
            'El plancton puede emitir luz',
            'La energía química produce destellos',
            'Este fenómeno no es electricidad',
            'La bioluminiscencia también aparece en océanos',
            'Algunas especies pueden defenderse',
            'Otros animales utilizan señales luminosas',
            'La luz puede sorprender por su intensidad',
            'Observarla es una experiencia espectacular',
            '¿Por qué brilla el mar de noche?',
        ]
        issues = topic_problems('¿Por qué brilla el mar de noche?',
                                [{'line': line} for line in lines],
                                title='El misterioso mar brillante',
                                anchors=['mar', 'bioluminiscencia', 'luz'])
        self.assertEqual(issues, [])

    def test_general_topic_rejects_an_unrelated_story(self):
        scenes = [{'line': 'El nuevo edificio tiene muchas oficinas'} for _ in range(12)]
        scenes += [{'line': '¿Qué te parece esta empresa?'}]
        problems = topic_problems('Agujeros negros', scenes,
                                   title='Un edificio impresionante',
                                   anchors=['agujeros negros', 'gravedad'])
        self.assertTrue(problems)
