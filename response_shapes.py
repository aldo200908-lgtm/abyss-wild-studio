"""Validadores estrictos para respuestas JSON de Gemini.

Se toleran envoltorios JSON y listas de escenas, pero no datos ausentes o
incorrectos. La seguridad factual se comprueba además en pipeline.py.
"""

def normalize_script_payload(payload, topic):
    """Devuelve {title, scenes} o None. No inventa hechos ni escenas."""
    if isinstance(payload, dict):
        if isinstance(payload.get('scenes'), list):
            candidate = payload
        else:
            candidate = None
            for name in ('result', 'script', 'video', 'data', 'output'):
                value = payload.get(name)
                if isinstance(value, (list, dict)):
                    candidate = normalize_script_payload(value, topic)
                    if candidate is not None:
                        break
            if candidate is None:
                return None
    elif isinstance(payload, list):
        if len(payload) == 1 and isinstance(payload[0], dict) and 'scenes' in payload[0]:
            return normalize_script_payload(payload[0], topic)
        if not payload or not all(isinstance(scene, dict) and 'line' in scene for scene in payload):
            return None
        candidate = {'title': topic, 'scenes': payload}
    else:
        return None

    scenes = candidate['scenes']
    if not 10 <= len(scenes) <= 20:
        return None
    clean_scenes = []
    for scene in scenes:
        if not isinstance(scene, dict):
            return None
        line = scene.get('line')
        facts = scene.get('fact_ids')
        if not isinstance(line, str) or not line.strip() or not isinstance(facts, list):
            return None
        if any(not isinstance(i, str) for i in facts):
            return None
        clean = dict(scene)
        clean['line'] = line.strip()
        clean['fact_ids'] = facts
        if not isinstance(clean.get('visual_type'), str) or clean.get('visual_type') not in (
                'photo', 'object', 'fossil', 'landscape', 'reconstruction', 'diagram', 'infographic'):
            clean['visual_type'] = 'infographic'
        if not isinstance(clean.get('visual_query'), str):
            clean['visual_query'] = ''
        if not isinstance(clean.get('label'), str):
            clean['label'] = 'DATO VERIFICADO'
        clean_scenes.append(clean)
    title = candidate.get('title', topic)
    if not isinstance(title, str) or not title.strip():
        title = topic
    return {'title': title.strip(), 'scenes': clean_scenes}


def normalize_audit_payload(payload, scene_count):
    """Lista de índices rechazados, o None cuando el auditor no es interpretable."""
    if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
        payload = payload[0]
    if isinstance(payload, dict):
        payload = payload.get('rejected')
    if not isinstance(payload, list):
        return None
    if any(type(i) is not int or i < 0 or i >= scene_count for i in payload):
        return None
    return sorted(set(payload))
