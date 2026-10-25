"""Text preparation for native Spanish TTS. No translation or fact invention."""
import json
import re
from datetime import date
from pathlib import Path
from num2words import num2words

UNITS = {
    'km': 'kilómetros', 'kg': 'kilos', 'cm': 'centímetros',
    'mm': 'milímetros', 'm': 'metros', 'g': 'gramos',
    't': 'toneladas', '°c': 'grados Celsius', '%': 'por ciento',
}
MONTHS = ('enero febrero marzo abril mayo junio julio agosto septiembre '
          'octubre noviembre diciembre').split()
WORD = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:['’][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)?")
NUMBER = r'\d{1,3}(?:\.\d{3})+|\d+(?:,\d+)?|\d+'


def number_es(digits):
    raw = digits.replace(' ', '')
    if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', raw):
        value = int(raw.replace('.', ''))
        return num2words(value, lang='es')
    if ',' in raw:
        whole, decimal = raw.split(',', 1)
        return num2words(int(whole), lang='es') + ' coma ' + ' '.join(
            num2words(int(d), lang='es') for d in decimal)
    return num2words(int(raw), lang='es')


def normalizar(texto):
    """Return spoken Spanish, expanding units, intervals, dates and acronyms.

    Unknown all-uppercase abbreviations fail closed instead of being spelled
    ambiguously by TTS. Call this before phonetic replacements.
    """
    text = str(texto).strip()
    text = (text.replace('“', '').replace('”', '').replace('«', '')
            .replace('»', '').replace('"', '').replace('…', '.')
            .replace('—', ' a ').replace('–', ' a ').replace('−', ' menos ')
            .replace('º', ' grados ').replace('ª', ' '))
    text = re.sub(r'\b(aprox|aproximad|aprox)\.\s*', 'aproximadamente ', text, flags=re.I)
    substitutions = {'ADN': 'ácido desoxirribonucleico',
                     'IA': 'inteligencia artificial',
                     'EEUU': 'Estados Unidos',
                     'EE.UU.': 'Estados Unidos',
                     'ONU': 'Organización de las Naciones Unidas',
                     'GPS': 'sistema de posicionamiento global'}
    for acronym, expanded in sorted(substitutions.items(), key=lambda p: -len(p[0])):
        text = re.sub(r'(?<!\w)' + re.escape(acronym) + r'(?!\w)', expanded, text)
    def as_date(m):
        d, mo, yr = map(int, m.groups())
        date(yr, mo, d)  # Real calendar validation.
        return (num2words(d, lang='es') + ' de ' + MONTHS[mo - 1] +
                ' de ' + num2words(yr, lang='es'))
    text = re.sub(r'(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)', as_date, text)

    # Ranges before the single-number rule: "12-14 m", "12 a 14 km".
    units = '|'.join(sorted(UNITS, key=len, reverse=True))
    range_re = rf'(?<![\w.])({NUMBER})\s*(?:-|a)\s*({NUMBER})\s*({units})(?!\w)'
    def expand_range(m):
        u = m.group(3).lower()
        return f'{number_es(m.group(1))} a {number_es(m.group(2))} {UNITS[u]}'
    text = re.sub(range_re, expand_range, text, flags=re.I)

    def expand_num(m):
        return number_es(m.group(0))
    text = re.sub(rf'(?<![\w.])(?:{NUMBER})(?!\w)', expand_num, text)

    for unit, spoken in sorted(UNITS.items(), key=lambda x: -len(x[0])):
        if unit == '%':
            text = text.replace('%', ' por ciento ')
        else:
            text = re.sub(r'(?<!\w)' + re.escape(unit) + r'\b', spoken, text, flags=re.I)

    # Standalone symbol, always unambiguous.
    text = text.replace('&', ' y ').replace('+', ' más ').replace('=', ' igual a ')
    text = re.sub(r'(?<!\w)[(){}\[\]](?!\w)?', ' ', text)
    text = re.sub(r'[()]', ' ', text)
    text = re.sub(r'\s*[-–]\s*', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    # Spanish conjunction: "u" only before words beginning with o/ho;
    # "o" becomes "u" in those contexts.
    text = re.sub(r'\b(o|u)\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)',
                  lambda m: ('u' if m.group(2).lower().startswith(('o', 'ho'))
                             else 'o') + ' ' + m.group(2),
                  text, flags=re.I)
    # Unexplained acronyms risk letter-by-letter English output.
    unknown = re.findall(r'(?<!\w)[A-ZÁÉÍÓÚÑ]{2,}(?!\w)', text)
    if unknown:
        raise ValueError('Siglas sin explicar en el guion: ' + ', '.join(unknown))
    return text


def load_dictionary(path):
    entries = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(entries, dict):
        raise ValueError('pronunciacion.json debe contener un objeto')
    cleaned = {}
    for term, item in entries.items():
        if not term or not isinstance(item, dict) or not isinstance(item.get('hablado'), str):
            raise ValueError('Diccionario con entrada no válida: ' + str(term))
        if not item['hablado'].strip():
            raise ValueError('Pronunciación vacía: ' + term)
        cleaned[term] = item['hablado']
    return cleaned


def fonetizar(text, dictionary):
    """Longest term first; one replacement per original span."""
    if not dictionary:
        return text
    alternatives = sorted(dictionary, key=len, reverse=True)
    regex = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(w) for w in alternatives) +
                       r')(?!\w)', re.I)
    lower = {key.casefold(): value for key, value in dictionary.items()}
    return regex.sub(lambda m: lower[m.group(0).casefold()], text)


def palabras(text):
    return WORD.findall(text)


def grupos_de_frases(scenes, minimum=8, maximum=18):
    """Combine 4-9 word scene lines into clauses with 8-18 words.

    Preserve scene order and do not rewrite factual content. If a single scene
    is > max words, fail rather than splitting its semantics blindly.
    """
    if not 1 <= minimum <= maximum:
        raise ValueError('Rango de palabras inválido')
    groups = []
    current = []
    current_words = 0
    for index, text in enumerate(scenes):
        length = len(palabras(text))
        if length > maximum:
            raise ValueError(f'Escena {index+1} demasiado larga para locución ({length})')
        if current and current_words + length > maximum:
            groups.append(current)
            current, current_words = [], 0
        current.append((index, text))
        current_words += length
    if current:
        groups.append(current)
    # Merge short tail when possible.
    if len(groups) > 1 and sum(len(palabras(t)) for _, t in groups[-1]) < minimum:
        tail = groups[-1]
        prev = groups[-2]
        if sum(len(palabras(t)) for _, t in prev + tail) <= maximum:
            groups[-2] += tail
            groups.pop()
    # A short residual phrase can still occur for very short scripts; fail.
    for group in groups:
        n = sum(len(palabras(t)) for _, t in group)
        if n < minimum or n > maximum:
            raise ValueError(f'No se pueden formar frases de {minimum}-{maximum} palabras; '
                             f'frase de {n} palabras')
    return groups
