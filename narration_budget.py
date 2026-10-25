"""Voice-aware duration preflight and non-fabricating scene reduction.

Calibrated for the slow Spanish neural speech in the Oct-2026 test:
a 103-word Titanoboa script took 52.4 seconds. This is an estimate,
never a substitute for actual duration measured after Azure synthesis.
"""
from copy import deepcopy

from spanish_voice_text import normalizar, palabras, grupos_de_frases

# Conservative for the currently selected Jorge Neural at -2%.
SECONDS_PER_SPOKEN_WORD = 0.485
PAUSE_PER_GROUP = 0.35
ESTIMATE_MARGIN = 0.6
MAX_PREVIEW_SECONDS = 43.5


def spoken_word_count(scenes):
    return sum(len(palabras(normalizar(s['line']))) for s in scenes)


def predict_duration(scenes, config):
    normalized = [normalizar(s['line']) for s in scenes]
    groups = grupos_de_frases(normalized,
                              int(config['phrase_min_words']),
                              int(config['phrase_max_words']))
    words = sum(len(palabras(s)) for s in normalized)
    pause = float(config['pause_max_seconds'] +
                  config['pause_min_seconds']) / 2
    return round(words * SECONDS_PER_SPOKEN_WORD +
                 max(0, len(groups) - 1) * pause +
                 ESTIMATE_MARGIN, 2)


def remove_secondary_scene(scenes):
    """Remove one middle scene WITHOUT rewriting approved factual statements.

    Opening two and final two scenes are preserved for clear hook and ending.
    Only call this on an already verified script; it never creates facts.
    """
    if len(scenes) <= 8:
        return None
    available = list(range(2, len(scenes) - 2))
    if not available:
        return None
    middle = (len(scenes) - 1) / 2
    # More spoken words saved while keeping important opening/conclusion.
    ranked = sorted(available, key=lambda i: (
        -len(palabras(normalizar(scenes[i]['line']))),
        abs(i - middle), i))
    cut = ranked[0]
    result = deepcopy(scenes)
    dropped = result.pop(cut)
    return result, cut, dropped
