"""Generic topic focus checks for any subject or question.

A lexical gate is a fast defense against obvious drift. The independent
Gemini relevance auditor in pipeline.py provides a semantic gate as well.
Neither constitutes a guarantee of factual correctness.
"""
import re
from topic_research import fold, keywords


def canon(value):
    return ''.join(c for c in fold(value) if c.isalnum())


def stems(value):
    # Light morphology tolerance (serpiente/serpientes, estrellas/estrella).
    return {w[:6] if len(w) > 7 else w[:5] if len(w) > 5 else w
            for w in keywords(value) if len(w) >= 3}


def topic_problems(topic, scenes, title='', anchors=None):
    problems = []
    if not isinstance(topic, str) or not topic.strip():
        return ['Tema vacío']
    if not isinstance(scenes, list) or len(scenes) < 3:
        return ['Escenas insuficientes']
    if any(not isinstance(s, dict) or not isinstance(s.get('line'), str)
           for s in scenes):
        return ['Escenas con formato incorrecto']
    lines = [s['line'] for s in scenes]
    if not isinstance(anchors, list):
        anchors = []
    subject = keywords(topic)
    # A single named subject must appear by name in title, hook and question.
    proper_subject = (len(subject) == 1 and len(subject[0]) >= 5 and
                      '?' not in topic and '¿' not in topic and
                      not fold(topic).strip().startswith(('por que', 'como ', 'que ',
                                                         'cuando ', 'donde ')))
    if proper_subject:
        word = canon(subject[0])
        if word not in canon(' '.join(lines[:3])):
            problems.append('El gancho no menciona el tema solicitado')
        if word not in canon(lines[-1]):
            problems.append('La pregunta no menciona el tema')
        if title and word not in canon(title):
            problems.append('El título no menciona el tema')
    anchors = [topic] + anchors[:6]
    keyset = set().union(*(stems(a) for a in anchors))
    if not keyset:
        return ['No hay palabras clave para validar el enfoque']

    def score(sentence):
        return len(stems(sentence) & keyset)

    if not any(score(line) > 0 for line in lines[:3]):
        problems.append('El inicio no está conectado con el asunto solicitado')
    if not any(score(line) > 0 for line in lines[-2:]):
        problems.append('El final no está conectado con el asunto solicitado')
    # The audience should not get 12 scenes of background context.
    relevant = sum(score(line) > 0 for line in lines[:-1])
    needed = max(3, (len(lines) - 1) // 3)
    if relevant < needed:
        problems.append(f'Solo {relevant} de {len(lines)-1} escenas contienen '
                        'conceptos centrales del tema')
    if title and not score(title):
        problems.append('Título sin relación léxica con el tema')
    return problems
