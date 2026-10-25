"""Constrained revisions for individual rejected narration scenes.

No rejected scene can be silently approved. Every repair still needs
an independent factual/editorial audit after application.
"""
import copy
import re


def line_words(text):
    return re.findall(r"[\wÁÉÍÓÚÜÑáéíóúüñ]+(?:['’][\w]+)?",
                      text, re.UNICODE)


def apply_scene_repairs(scenes, proposal, rejected, known_ids):
    """Return safely amended scenes, or None for malformed/unsafe edits.

    The audit indices refer only to factual scenes (never the last question).
    Only explicitly rejected lines can be changed.
    """
    if not isinstance(scenes, list) or len(scenes) < 3:
        return None
    if not rejected or len(set(rejected)) != len(rejected):
        return None
    if any(type(i) is not int or i < 0 or i >= len(scenes) - 1
           for i in rejected):
        return None
    if isinstance(proposal, list) and len(proposal) == 1 and isinstance(proposal[0], dict):
        proposal = proposal[0]
    if not isinstance(proposal, dict):
        return None
    replacements = proposal.get('replacements')
    if not isinstance(replacements, list) or len(replacements) != len(rejected):
        return None
    allowed = set(rejected)
    seen = set()
    revised = copy.deepcopy(scenes)
    for item in replacements:
        if not isinstance(item, dict):
            return None
        idx = item.get('index')
        if type(idx) is not int or idx not in allowed or idx in seen:
            return None
        seen.add(idx)
        text = item.get('line')
        cited = item.get('fact_ids')
        if not isinstance(text, str) or not 4 <= len(line_words(text)) <= 10:
            return None
        if not isinstance(cited, list) or not 1 <= len(cited) <= 2:
            return None
        if any(not isinstance(fid, str) or fid not in known_ids
               for fid in cited):
            return None
        # Prevent superficial resubmission of exactly the same rejected line.
        if text.strip().casefold() == scenes[idx].get('line', '').strip().casefold():
            return None
        fixed = dict(revised[idx])
        fixed['line'] = text.strip()
        fixed['fact_ids'] = cited
        fixed['compare_m'] = None  # Drop measurement unless re-validated later.
        visual_type = item.get('visual_type')
        if visual_type in ('photo', 'object', 'fossil', 'landscape',
                           'reconstruction', 'diagram', 'infographic'):
            fixed['visual_type'] = visual_type
        q = item.get('visual_query')
        if isinstance(q, str):
            fixed['visual_query'] = q.strip()[:90]
        # No model-supplied URL or unrestricted file path is copied.
        revised[idx] = fixed
    if seen != allowed:
        return None
    count = sum(len(line_words(scene.get('line', ''))) for scene in revised)
    if not 62 <= count <= 112:
        return None
    return revised
