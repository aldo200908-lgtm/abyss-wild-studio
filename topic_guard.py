"""Deterministic editorial gate: a sourced script must still be ON TOPIC.

Not a semantic proof; prevents obvious topic drift like a Titanoboa
video about coal beds and mining economics.
"""
import re
import unicodedata


def canon(value):
    value = unicodedata.normalize('NFKD', str(value).lower())
    return ''.join(c for c in value if c.isalnum() and
                   not unicodedata.combining(c))


def topic_problems(topic, scenes, title=''):
    problems = []
    subject = canon(topic)
    if not subject or not isinstance(scenes, list) or len(scenes) < 3:
        return ['Tema o lista de escenas inválidos']
    lines = [str(s.get('line', '')) if isinstance(s, dict) else ''
             for s in scenes]
    if subject not in canon(' '.join(lines[:3])):
        problems.append('El gancho inicial no menciona el tema solicitado')
    if subject not in canon(lines[-1]):
        problems.append('La pregunta final no trata directamente del tema')
    if title and subject not in canon(title):
        problems.append('El título no contiene el tema')

    if subject == 'titanoboa':
        # The video must be ABOUT the giant snake, not the mining site
        # where the fossils were found. A single geographical aside is fine.
        distractors = ('carbón', 'minería', 'económico', 'yacimiento',
                       'lechos', 'explotado', 'formación se subdivide',
                       'recurso mineral', 'campos de hulla')
        drift = sum(any(canon(term) in canon(line) for term in distractors)
                    for line in lines)
        if drift >= 2:
            problems.append(
                f'{drift} escenas centradas en carbón/minería, no Titanoboa')
        scientific = ('titanoboa', 'serpiente', 'reptil', 'vértebra',
                      'fósil', 'gigante', 'longitud', 'presa', 'tamaño',
                      'metros', 'pesaba', 'cuerpo', 'selva')
        relevant = sum(any(canon(term) in canon(line) for term in scientific)
                       for line in lines[:-1])
        if relevant < 6:
            problems.append(
                f'Solo {relevant} escenas describen al animal o su hábitat')
    return problems
