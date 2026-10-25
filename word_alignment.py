"""Reliable one-word subtitle timestamps from Whisper word-level ASR.

Word-level Whisper alignment is approximate (ASR, not phoneme forced align).
Unrecognized tokens retain the measured TTS phrase estimate, clearly flagged.
Digit tokens are expanded using the same Spanish converter used by the voice.
"""
from difflib import SequenceMatcher
import re
import unicodedata

from spanish_voice_text import NUMBER, number_es


def lexical(text):
    text = str(text).casefold()
    text = re.sub(rf'(?<![\w.])(?:{NUMBER})(?!\w)',
                  lambda m: number_es(m.group(0)), text)
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.findall(r'[a-z0-9]+', text)


def sync_words(script_marks, whisper_words, duration):
    """Return exactly the authored words, timed to actual Whisper word boundaries."""
    if not whisper_words:
        return script_marks, {'method': 'measured_tts_phrase_estimate',
                              'matched_ratio': 0}
    expected = [lexical(m['text']) for m in script_marks]
    if any(len(t) != 1 for t in expected):
        raise ValueError('Una palabra por marca TTS es obligatorio')
    heard_tokens, source_ranges = [], []
    for source in whisper_words:
        terms = lexical(source.get('text', ''))
        if not terms:
            continue
        start, end = float(source['start']), float(source['end'])
        if start < 0 or end <= start:
            continue
        n = len(terms)
        for i, word in enumerate(terms):
            heard_tokens.append(word)
            source_ranges.append((start + (end-start)*i/n,
                                  start + (end-start)*(i+1)/n))
    if not heard_tokens:
        return script_marks, {'method': 'measured_tts_phrase_estimate',
                              'matched_ratio': 0}
    original = [x[0] for x in expected]
    match = SequenceMatcher(a=original, b=heard_tokens, autojunk=False)
    found = {}
    for block in match.get_matching_blocks():
        for n in range(block.size):
            found[block.a+n] = source_ranges[block.b+n]
    aligned = []
    for i, m in enumerate(script_marks):
        start,end = found.get(i, (float(m['start']),float(m['end'])))
        aligned.append({'text': m['text'], 'start': max(0., min(duration, start)),
                        'end': max(0., min(duration, end))})
    # Resolve accidental overlaps and bound all word durations to audio.
    # Whisper can group multiple tokens (186); their segment is subdivided.
    for i, m in enumerate(aligned):
        m['start'] = max(0., min(duration-.01, m['start']))
        m['end'] = max(m['start']+.01, min(duration, m['end']))
        if i and m['start'] < aligned[i-1]['end']:
            overlap = aligned[i-1]['end']-m['start']
            if overlap < .25:
                aligned[i-1]['end'] = max(aligned[i-1]['start']+.01,m['start'])
            else:
                m['start'] = aligned[i-1]['end']
                m['end'] = max(m['start']+.01, m['end'])
        if m['end'] > duration:
            m['end'] = duration
    ratio=len(found)/len(script_marks) if script_marks else 0
    return aligned, {'method': 'whisper_word_timestamps_with_tts_gap_fill',
                     'matched_ratio': round(ratio,4)}
