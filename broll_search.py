"""Search plans and safe B-roll reuse for factual short documentaries.

A scene can use an already licensed/reviewed TOPIC shot as illustrative
context, provided a fresh scene-specific visual audit agrees. For example,
a reconstruction of Titanoboa can accompany narration about the Paleocene;
it is NOT presented as original footage of that ancient period.
"""
import re


def search_terms(topic, scene):
    subject = str(topic).strip()[:90]
    query = str(scene.get('visual_query') or '').strip()[:90]
    line = str(scene.get('line') or '').casefold()
    visual = str(scene.get('visual_type') or '').casefold()

    terms = [query, subject, f'{subject} reconstruction',
             f'{subject} museum model', f'{subject} fossil',
             f'{subject} scientific illustration']
    if re.search(r'paleoceno|paleocene', line):
        terms.extend(['Paleocene rainforest reconstruction',
                      'Paleocene tropical forest paleoart',
                      f'{subject} Paleocene fossil'])
    elif re.search(r'eoceno|eocene', line):
        terms.extend(['Eocene forest reconstruction',
                      f'{subject} Eocene fossil'])
    elif re.search(r'museo|esqueleto|vértebra|fósil|cráneo|hueso', line):
        terms.extend([f'{subject} fossil vertebra',
                      f'{subject} museum skeleton'])
    if visual in ('landscape', 'environment'):
        terms.extend([f'{subject} habitat reconstruction',
                      'tropical rainforest natural landscape'])
    # Stable order, unique terms: broader subject terms remain available
    # when LLM-generated visual_query gives no useful Commons result.
    unique = set()
    result = []
    for term in terms:
        term = term.strip()
        if term and term.casefold() not in unique:
            unique.add(term.casefold())
            result.append(term)
    return result


def reorder_fallback_assets(previous, scene_index):
    """Nearest already approved source first, stable deterministic order."""
    return sorted(previous, key=lambda row: (
        abs(row['scene_index']-scene_index),
        row['scene_index']))


def allowed_illustrative_reuse(visual_audit):
    """Never reuse a rejected visual, even if it passed an earlier scene."""
    return (isinstance(visual_audit, dict)
            and visual_audit.get('match') is True)
