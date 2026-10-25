"""Topic-adaptive Wikimedia research helpers.

A topic may be a noun, a question or a creative brief. Only explicitly
selected Wikipedia articles become factual evidence; never infer facts from
search snippets or the language model's prior knowledge.
"""
import re
import unicodedata

STOP = set("""a al algo ante bajo con contra cual cuales cuando de del desde
donde el ella en entre era eres es esa ese eso esta este esto fue ha hay la
las lo los mas me mi muy ni no o para pero por porque que quien se si sin
sobre son su sus te tu un una uno unos unas y ya como cual es cuanto
cuales qué cómo cuál dónde cuándo quépor porqué los las historia dato datos
explica explicacion explicame muestra video shorts sobre hacer""".split())


def fold(text):
    txt = unicodedata.normalize('NFKD', str(text).lower())
    return ''.join(c for c in txt if not unicodedata.combining(c))


def keywords(text):
    parts = re.findall(r'[a-z0-9ñ]{3,}', fold(text))
    return [part for part in parts if part not in STOP]


def short_query(text):
    return ' '.join(keywords(text)[:6])[:95]


def list_of_strings(value, maximum, length=80):
    if not isinstance(value, list):
        return []
    items = []
    for element in value:
        if isinstance(element, str):
            term = re.sub(r'\s+', ' ', element).strip()[:length]
            if term and term.casefold() not in {p.casefold() for p in items}:
                items.append(term)
        if len(items) >= maximum:
            break
    return items


def topic_plan(topic, gm):
    """Create search terms from the user's idea without inventing citations."""
    prompt = (
        'Planea SOLO búsquedas enciclopédicas para investigar esta idea de vídeo: '
        + repr(topic) + '. El objetivo es el asunto central, no un lugar, '
        'mineral, personaje secundario o artículo que solo lo menciona. '
        'Responde JSON objeto con las claves: '
        '{"focus":"asunto central preciso",'
        '"queries_es":["búsqueda enciclopédica 1","búsqueda 2"],'
        '"queries_en":["search 1"],'
        '"anchors":["término central","sinónimo directo"],'
        '"visual_exclusions":["elemento visual que se podría confundir"]}. '
        'Máximo 3 consultas ES, 2 EN, 6 anclas, 5 exclusiones. '
        'No incluyas datos científicos ni afirmaciones sobre el tema; '
        'solo términos de búsqueda. Si el tema es una pregunta, identifica '
        'el fenómeno que permitiría responderla. No cambies de tema.'
    )
    raw = gm.generate(prompt, temperature=0)
    if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], dict):
        raw = raw[0]
    if not isinstance(raw, dict):
        raw = {}
    focus = raw.get('focus')
    if not isinstance(focus, str) or not focus.strip():
        focus = topic
    plan = {
        'topic': topic,
        'focus': focus.strip()[:110],
        'queries_es': list_of_strings(raw.get('queries_es'), 3),
        'queries_en': list_of_strings(raw.get('queries_en'), 2),
        'anchors': list_of_strings(raw.get('anchors'), 6, 55),
        'visual_exclusions': list_of_strings(raw.get('visual_exclusions'), 5, 50)
    }
    if not plan['anchors']:
        plan['anchors'] = [plan['focus']]
    return plan


def queries(topic, plan):
    es = [topic, plan['focus'], short_query(topic)] + plan['queries_es']
    en = plan['queries_en']
    results = []
    for lang, items, maximum in (('es', es, 5), ('en', en, 2)):
        for q in items:
            q = str(q).strip()
            if len(q) < 3 or any(l == lang and old.casefold() == q.casefold()
                                for l, old in results):
                continue
            results.append((lang, q))
            if sum(l == lang for l, _ in results) >= maximum:
                break
    return results


def gather_candidates(topic, plan, wiki_api):
    """Search two language editions, without treating matches as evidence."""
    catalog, known = [], set()
    for lang, q in queries(topic, plan):
        try:
            hits = wiki_api({'action': 'query', 'list': 'search',
                             'srsearch': q, 'srnamespace': 0,
                             'srlimit': 6}, lang=lang)['query']['search']
        except (KeyError, TypeError, ValueError):
            continue
        for hit in hits:
            title = hit.get('title', '')
            key = (lang, fold(title))
            if not title or key in known:
                continue
            known.add(key)
            catalog.append({
                'id': f'A{len(catalog)+1}', 'lang': lang, 'title': title,
                'snippet': re.sub(r'<[^>]*>', ' ', hit.get('snippet', ''))[:280]
            })
    return catalog[:32]


def candidate_selection(topic, plan, catalog, gm):
    """Return only catalog entries explicitly selected as on-topic by Gemini."""
    if not catalog:
        return []
    concise = [{'id': row['id'], 'lang': row['lang'],
                'title': row['title'], 'snippet': row['snippet']} for row in catalog]
    prompt = (
        'Filtra resultados de Wikipedia para INVESTIGAR el tema del Short. '
        'Solicitud exacta: ' + repr(topic) + '. Foco: '
        + repr(plan['focus']) + '. '
        'Selecciona de 1 a 3 artículos que sean SOBRE EL TEMA '
        'o expliquen directamente su fenómeno central. Nunca elijas '
        'un lugar de hallazgo, compañía, yacimiento o contexto periférico '
        'que únicamente mencione el tema; si nada sirve devuelve lista vacía. '
        'Para una pregunta amplia puedes elegir artículos sobre fenómenos '
        'científicos directamente pertinentes. Los snippets solo sirven para '
        'elegir; NO son pruebas de hechos. '
        'Responde estrictamente JSON objeto {"selected":["A1","A2"]}. '
        'Usa únicamente IDs del catálogo. Catálogo: '
        + __import__('json').dumps(concise, ensure_ascii=False)
    )
    raw = gm.generate(prompt, temperature=0)
    if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], dict):
        raw = raw[0]
    if not isinstance(raw, dict) or not isinstance(raw.get('selected'), list):
        return []
    index = {row['id']: row for row in catalog}
    chosen, used = [], set()
    for selected in raw['selected']:
        if selected in index and selected not in used:
            chosen.append(index[selected])
            used.add(selected)
        if len(chosen) >= 3:
            break
    return chosen


def extract_sentences(pages, minimum=4, maximum=85):
    facts, sources = [], []
    for lang, p in pages:
        title = str(p.get('title', '')).strip()
        extract = str(p.get('extract', '')).split('\nReferencias\n')[0]
        extract = extract.split('\nEnlaces externos\n')[0]
        if not title or not extract.strip():
            continue
        url = 'https://' + lang + '.wikipedia.org/wiki/' + (
            __import__('urllib.parse', fromlist=['quote']).quote(
                title.replace(' ', '_')))
        # Keep newlines long enough to split article headings.
        plain = re.sub(r'\s+', ' ', extract).strip()
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÑ0-9])', plain)
        taken = []
        for sentence in sentences:
            if 35 <= len(sentence) <= 360:
                taken.append(sentence)
        if not taken:
            continue
        sources.append({'title': title, 'url': url, 'lang': lang})
        for sentence in taken:
            if len(facts) >= maximum:
                break
            facts.append({'id': f'F{len(facts)+1}',
                          'text': sentence, 'url': url, 'lang': lang})
    if len(facts) < minimum:
        raise RuntimeError('No hay suficiente evidencia enciclopédica sobre el tema; '
                           'no se fabricará un guion con datos no comprobados.')
    return facts, sources


def fetch_selected_articles(chosen, wiki_api):
    pages = []
    for item in chosen:
        lang = item['lang']
        result = wiki_api({'action': 'query', 'prop': 'extracts',
                           'titles': item['title'], 'redirects': 1,
                           'explaintext': 1, 'exchars': 18000}, lang=lang)
        for page in result.get('query', {}).get('pages', []):
            if ('missing' not in page and page.get('extract') and
                    fold(page.get('title')) == fold(item['title'])):
                pages.append((lang, page))
    return pages
