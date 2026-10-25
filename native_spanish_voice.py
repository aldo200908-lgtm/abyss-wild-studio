"""Native es-* voice, strict locale validation, per-phrase synthesis and Whisper QA.

Requires Azure Speech resource in AZURE_SPEECH_KEY / AZURE_SPEECH_REGION.
Never routes to edge-tts, non-Spanish voices, Piper or eSpeak as fallback.
"""
import json
import random
import re
import subprocess
import tempfile
import wave
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import numpy as np
from spanish_voice_text import (normalizar, fonetizar, load_dictionary,
                                palabras, grupos_de_frases, NUMBER, number_es)

class NarrationDurationError(RuntimeError):
    """Measured natural voice is outside the allowed video length."""
    def __init__(self, seconds):
        self.seconds = float(seconds)
        super().__init__(
            f'Locución española de {seconds:.1f}s fuera de 30–45s; '
            'acortar el guion verificado sin acelerar la voz')


VOICES = (
    'es-PE-AlexNeural', 'es-PE-CamilaNeural',
    'es-CO-GonzaloNeural', 'es-CO-SalomeNeural', 'es-MX-JorgeNeural',
)
VOICE_PATTERN = re.compile(r'^es-[A-Z]{2}-[A-Za-z]+Neural$')


def config_from(path):
    cfg = json.loads(Path(path).read_text(encoding='utf-8'))
    voice = cfg.get('voice')
    if not isinstance(voice, str) or not VOICE_PATTERN.fullmatch(voice):
        raise ValueError('config.json: voice debe ser es-XX-NombreNeural, '
                         'no se permiten voces Multilingual ni de otro idioma')
    if voice not in VOICES:
        raise ValueError('Voz no autorizada en config.json: ' + voice)
    if cfg.get('tts_provider') != 'azure':
        raise ValueError('tts_provider debe ser azure; no se autoriza respaldo alterno')
    if cfg.get('strict_no_fallback') is not True or cfg.get('verify_voice_locale') is not True:
        raise ValueError('No se puede desactivar validación de Locale ni habilitar fallback')
    rate = cfg.get('rate_percent')
    if not isinstance(rate, int) or not -4 <= rate <= 0:
        raise ValueError('rate_percent debe ser entero entre -4 y 0')
    if not 0.2 <= float(cfg.get('pause_min_seconds', 0)) <= float(
            cfg.get('pause_max_seconds', 0)) <= 0.5:
        raise ValueError('Pausas permitidas 0.2–0.5 segundos')
    if cfg.get('whisper_language') != 'es':
        raise ValueError('El idioma de Whisper debe ser es')
    if not 0.92 <= float(cfg.get('min_transcription_match', 0)) <= 1.0:
        raise ValueError('Whisper debe exigir al menos 92 por ciento')
    return cfg


def validate_locale(voice_id, available):
    if not VOICE_PATTERN.fullmatch(voice_id) or voice_id not in VOICES:
        raise RuntimeError('Voz no española o no autorizada: ' + str(voice_id))
    for voice in available:
        short = getattr(voice, 'short_name', None)
        locale = getattr(voice, 'locale', None)
        if short == voice_id:
            if not isinstance(locale, str) or not locale.startswith('es-'):
                raise RuntimeError('Locale inválido para ' + voice_id +
                                   ': se esperaba es-*, recibido ' + str(locale))
            if locale != voice_id[:5]:
                raise RuntimeError('Locale no coincide con el identificador ' +
                                   voice_id + ': ' + locale)
            return locale
    raise RuntimeError('La voz ' + voice_id +
                       ' no está disponible en el recurso de Azure de esta región')


class AzureSpanishSpeech:
    def __init__(self, key, region):
        if not key or not region:
            raise RuntimeError('Faltan Secrets AZURE_SPEECH_KEY y AZURE_SPEECH_REGION '
                               'en GitHub Actions. Sin ellos no se sintetiza voz.')
        import azure.cognitiveservices.speech as speechsdk
        self.sdk = speechsdk
        self.speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm)
        self.available = None

    def ensure_voice(self, voice_id):
        sdk = self.sdk
        if self.available is None:
            discovery = sdk.SpeechSynthesizer(
                speech_config=self.speech_config, audio_config=None)
            voices_result = discovery.get_voices_async('').get()
            if not getattr(voices_result, 'voices', None):
                raise RuntimeError('Azure no devolvió catálogo de voces. '
                                   'Verifica la región y la clave del servicio Speech.')
            self.available = voices_result.voices
        return validate_locale(voice_id, self.available)

    def synthesize(self, text, target, voice, rate=-2):
        locale = self.ensure_voice(voice)  # Before EVERY synthesis, no exceptions.
        if not isinstance(rate, int) or rate < -4 or rate > 0:
            raise ValueError('La velocidad debe estar entre -4% y 0%')
        speak = ("<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' "
                 f"xml:lang='{locale}'><voice name='{voice}'>"
                 f"<prosody rate='{rate:+d}%'>{xml_escape(text)}</prosody>"
                 "</voice></speak>")
        audio = self.sdk.audio.AudioOutputConfig(filename=str(target))
        synthesizer = self.sdk.SpeechSynthesizer(
            speech_config=self.speech_config, audio_config=audio)
        result = synthesizer.speak_ssml_async(speak).get()
        if result.reason != self.sdk.ResultReason.SynthesizingAudioCompleted:
            details = getattr(result, 'cancellation_details', None)
            raise RuntimeError('Azure Speech no pudo sintetizar ' + voice +
                               ': ' + str(getattr(details, 'error_details', details)))
        if not Path(target).is_file() or Path(target).stat().st_size < 1000:
            raise RuntimeError('Azure Speech devolvió audio vacío: ' + voice)


def pcm_data(filename):
    with wave.open(str(filename), 'rb') as f:
        if f.getnchannels() != 1 or f.getsampwidth() != 2:
            raise RuntimeError('Voz no es WAV mono PCM 16 bit: ' + str(filename))
        return f.getframerate(), f.readframes(f.getnframes())


def wordmarks_per_scene(scenes, scene_time_ranges):
    """Approximate timing; never claim Whisper word-level forced alignment."""
    marks = []
    for scene, (start, end) in zip(scenes, scene_time_ranges):
        words = palabras(scene['line'])
        if not words:
            raise RuntimeError('Escena sin palabras')
        weights = [max(1, len(w) / 3) for w in words]
        total = sum(weights)
        current = start
        for word, weight in zip(words, weights):
            delta = (end - start) * weight / total
            marks.append({'text': word, 'start': round(current, 3),
                          'end': round(current + delta, 3)})
            current += delta
    return marks


def trim_tts_wav(source, dest):
    """FFmpeg trims only the leading and trailing silence."""
    filt = ('silenceremove=start_periods=1:start_duration=0.035:'
            'start_threshold=-48dB,areverse,'
            'silenceremove=start_periods=1:start_duration=0.035:'
            'start_threshold=-48dB,areverse')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source),
                    '-af', filt, '-c:a', 'pcm_s16le', str(dest)], check=True)
    with wave.open(str(dest), 'rb') as w:
        length = w.getnframes() / w.getframerate()
    if length < .25:
        raise RuntimeError('Fragmento de TTS sin audio válido')
    return length


def render_native_voice(scenes, mp3_path, settings, dictionary, synth):
    """Voice source is normalized Spanish, not phonetic guesses in subtitles.

    Groups are 8-18 words; WAV snippets are combined using PCM and FFmpeg.
    No silent gap is inserted between FFmpeg-trimmed clauses.
    """
    normalized = [normalizar(s['line']) for s in scenes]
    groups = grupos_de_frases(normalized,
                               int(settings['phrase_min_words']),
                               int(settings['phrase_max_words']))
    wavs, group_map = [], []
    with tempfile.TemporaryDirectory(prefix='abyss_azure_') as tempdir:
        for index, group in enumerate(groups):
            full = '. '.join(text.rstrip(' .?!') for _, text in group) + '.'
            spoken = fonetizar(full, dictionary)
            path = Path(tempdir) / f'phrase_{index:02d}.wav'
            synth.synthesize(spoken, path, settings['voice'],
                            settings['rate_percent'])
            trimmed = Path(tempdir) / f'phrase_{index:02d}_trimmed.wav'
            trim_tts_wav(path, trimmed)
            wavs.append(pcm_data(trimmed))
            group_map.append([i for i, _ in group])
        rates = {r for r, _ in wavs}
        if len(rates) != 1:
            raise RuntimeError('Frecuencia de audio cambió entre frases')
        rate = rates.pop()
        combined = Path(tempdir) / 'voice_joined.wav'
        offset = 0
        ranges = [None] * len(scenes)
        gaps = []
        with wave.open(str(combined), 'wb') as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(rate)
            for ix, ((_, frames), indices) in enumerate(zip(wavs, group_map)):
                begin = offset / rate
                output.writeframes(frames)
                offset += len(frames) // 2
                end = offset / rate
                # Approximate scene ranges by normalized spoken word count.
                weights = [max(1, len(palabras(normalized[i])))
                           for i in indices]
                length = sum(weights)
                pos = begin
                for idx, weight in zip(indices, weights):
                    next_pos = pos + (end - begin) * weight / length
                    ranges[idx] = (pos, next_pos)
                    pos = next_pos
                # Join the clauses immediately: no synthetic pause is added.
        seconds = offset / rate
        if not 30 <= seconds <= 45:
            raise NarrationDurationError(seconds)
        mp3_path = Path(mp3_path)
        mp3_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                        '-i', str(combined), '-codec:a', 'libmp3lame',
                        '-q:a', '3', str(mp3_path)], check=True)
        marks = wordmarks_per_scene(scenes, ranges)
        return marks, seconds, {
            'voice': settings['voice'], 'locale': settings['voice'][:5],
            'phrases': len(groups), 'pauses': gaps,
            'normalized_text': ' '.join(normalized),
            'spoken_text': ' '.join(fonetizar(
                '. '.join(normalized), dictionary).split()),
            'timing': 'approximate per-scene; not verified word alignment',
            'provider': 'Azure Speech',
        }


def transcript_score(expected, observed):
    """WER-like token-level Levenshtein similarity, not just char overlap."""
    import unicodedata
    def toks(text):
        # Whisper writes some correctly spoken numbers in digits ("186")
        # instead of words ("ciento ochenta y seis"). Reuse the exact
        # Spanish number converter used for Azure narration.
        expanded = re.sub(rf'(?<![\w.])(?:{NUMBER})(?!\w)',
                          lambda m: number_es(m.group(0)), str(text))
        plain = unicodedata.normalize('NFKD', expanded.lower())
        plain = ''.join(c for c in plain if not unicodedata.combining(c))
        return re.findall(r'[a-zñ0-9]+', plain)
    a, b = toks(expected), toks(observed)
    if not a:
        return 0.0, []
    matrix = list(range(len(b) + 1))
    for i, word in enumerate(a, 1):
        next_row = [i]
        for j, heard in enumerate(b, 1):
            next_row.append(min(next_row[-1] + 1, matrix[j] + 1,
                                matrix[j - 1] + (word != heard)))
        matrix = next_row
    import difflib
    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    suspects = []
    for opcode, i1, i2, j1, j2 in matcher.get_opcodes():
        if opcode != 'equal':
            suspects.append({'esperado': ' '.join(a[i1:i2]),
                             'escuchado': ' '.join(b[j1:j2])})
    return max(0, 1 - matrix[-1] / len(a)), suspects


def whisper_quality(audio, expected, config, report_path):
    """Transcribe full final voice; persist suspicious words even on failure."""
    from faster_whisper import WhisperModel
    import os
    model = WhisperModel(config['whisper_model'], device='cpu',
                         compute_type='int8', cpu_threads=2)
    segments, info = model.transcribe(str(audio), language='es', beam_size=5,
                                     condition_on_previous_text=False, word_timestamps=True)
    segments = list(segments)
    heard = ' '.join(seg.text.strip() for seg in segments).strip()
    word_times = []
    for seg in segments:
        for word in (seg.words or []):
            if word.start is not None and word.end is not None:
                word_times.append({'text': word.word.strip(),
                                   'start': round(word.start, 3),
                                   'end': round(word.end, 3)})
    score, suspects = transcript_score(expected, heard)
    lines = [f'Voz: {config["voice"]}', 'Idioma de transcripción: es',
             f'Coincidencia léxica: {score:.2%}',
             f'Mínimo exigido: {config["min_transcription_match"]:.0%}',
             'Equivalencia numérica: cifras y números pronunciados '
             'en palabras se comparan de forma idéntica.',
             f'Transcripción detectada: {heard}',
             'Diferencias sospechosas (revisar por oído, no asumir error fonético):']
    for item in suspects[:80]:
        lines.append(f'- Original: "{item["esperado"]}" | Whisper: "{item["escuchado"]}"')
    if not suspects:
        lines.append('- Ninguna discrepancia léxica')
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if score < float(config['min_transcription_match']):
        raise RuntimeError('Whisper detectó coincidencia '
                           f'{score:.1%} inferior al mínimo de '
                           f'{config["min_transcription_match"]:.0%}; '
                           f'consulta {report_path}')
    return {'transcription': heard, 'transcription_match': round(score, 4),
            'suspect_words': suspects, 'word_timestamps': word_times}


def spectral_high_frequency_ratio(audio):
    """Measure voice energy above 4 kHz relative to all frequency energy."""
    p = subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i',
                        str(audio), '-ac', '1', '-ar', '24000',
                        '-f', 'f32le', '-'], capture_output=True, check=True)
    signal = np.frombuffer(p.stdout, dtype='<f4')
    if len(signal) < 1024:
        raise RuntimeError('Señal demasiado corta para espectro')
    power = np.abs(np.fft.rfft(signal[:min(len(signal), 24000 * 45)])) ** 2
    hz = np.fft.rfftfreq(min(len(signal), 24000 * 45), d=1 / 24000)
    return round(float(power[hz > 4000].sum() /
                       max(power.sum(), 1e-12)), 5)
