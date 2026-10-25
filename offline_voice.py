"""Offline Spanish narration: Piper (primary), eSpeak NG (rescue).

There is no reliance on Microsoft's unofficial Read Aloud WebSocket.
Word timings are interpolated estimates within precisely measured scene audio.
"""
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import wave

VOICE_NAME = 'es_MX-ald-medium'
VOICE_PAGE = ('https://huggingface.co/rhasspy/piper-voices/tree/main/'
              'es/es_MX/ald/medium')
VOICE_DIR = Path.home() / '.cache' / 'abyss-piper'


def words_in(text):
    return re.findall(r"[\wÁÉÍÓÚÜÑáéíóúüñ]+(?:['’][\w]+)?", text, re.UNICODE)


def estimate_wordmarks(scenes, ranges):
    """Proportional within each measured scene, NOT forced word alignment."""
    marks = []
    for scene, (start, end) in zip(scenes, ranges):
        words = words_in(scene['line'])
        if not words:
            raise RuntimeError('Escena sin palabras')
        weights = [max(1.3, sum(c.lower() in 'aeiouáéíóúü' for c in w)
                       + .25 * len(w)) for w in words]
        total = sum(weights)
        pos = start
        for word, weight in zip(words, weights):
            step = (end - start) * weight / total
            marks.append({'text': word, 'start': round(pos, 4),
                          'end': round(pos + step, 4)})
            pos += step
    return marks


def piper_engine():
    from piper import PiperVoice
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    model = VOICE_DIR / (VOICE_NAME + '.onnx')
    config = VOICE_DIR / (VOICE_NAME + '.onnx.json')
    if not model.is_file() or not config.is_file():
        subprocess.run([sys.executable, '-m', 'piper.download_voices',
                        '--data-dir', str(VOICE_DIR), VOICE_NAME],
                       check=True, timeout=180)
    if not model.is_file() or model.stat().st_size < 1_000_000:
        raise RuntimeError('Descarga de modelo Piper incompleta')
    return PiperVoice.load(str(model))


def write_scene_audio(scenes, tempdir, engine, voice=None):
    result = []
    for idx, scene in enumerate(scenes):
        phrase = scene['line'].strip()
        if not phrase.endswith(('.', '?', '!', '¿', '¡')):
            phrase += '.'
        target = Path(tempdir) / f'scene_{idx:02d}.wav'
        if engine == 'Piper':
            with wave.open(str(target), 'wb') as wav:
                voice.synthesize_wav(phrase, wav)
        else:
            subprocess.run(['espeak-ng', '-v', 'es', '-s', '180', '-a', '140',
                            '-w', str(target), phrase],
                           check=True, timeout=30,
                           stdout=subprocess.DEVNULL)
        with wave.open(str(target), 'rb') as wav:
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
                raise RuntimeError('Audio de voz no es PCM mono 16-bit')
            rate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
        if not frames:
            raise RuntimeError('Motor TTS devolvió audio vacío')
        result.append((rate, frames))
    return result


def narration(scenes, target):
    """Create MP3 and return (word marks, MP3 seconds, engine).

    Each scene is synthesized separately so its real start/end is known.
    Word starts inside the scene are approximate, not WordBoundary.
    """
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='abyss_voice_') as tempdir:
        try:
            model = piper_engine()
            segments = write_scene_audio(scenes, tempdir, 'Piper', model)
            engine = 'Piper'
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError,
                ImportError) as err:
            print(f'[ABYSS] Piper no disponible ({type(err).__name__}); '
                  'se usará eSpeak NG sin servidor externo.', flush=True)
            segments = write_scene_audio(scenes, tempdir, 'eSpeak NG')
            engine = 'eSpeak NG'
        sample_rates = {rate for rate, _ in segments}
        if len(sample_rates) != 1:
            raise RuntimeError('Frecuencias PCM diferentes entre escenas')
        rate = sample_rates.pop()
        joined = Path(tempdir) / 'narration.wav'
        ranges = []
        frames_total = 0
        silence = b'\x00\x00' * int(rate * 0.13)
        with wave.open(str(joined), 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            for idx, (_, frames) in enumerate(segments):
                if idx:
                    wav.writeframes(silence)
                    frames_total += len(silence) // 2
                start = frames_total / rate
                wav.writeframes(frames)
                frames_total += len(frames) // 2
                end = frames_total / rate
                ranges.append((start, end))
        raw_duration = frames_total / rate
        if raw_duration < 4:
            raise RuntimeError('Audio de voz demasiado corto')
        factor = raw_duration / 37.0 if not 30.2 <= raw_duration <= 44.4 else 1.0
        if not 0.5 <= factor <= 2.0:
            raise RuntimeError(f'Locución {raw_duration:.1f}s no permite '
                               'ajuste de velocidad razonable')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                        '-i', str(joined), '-af', f'atempo={factor:.6f}',
                        '-codec:a', 'libmp3lame', '-q:a', '3', str(target)],
                       check=True, timeout=90)
        r = subprocess.run(['ffprobe', '-v', 'error',
                            '-show_entries', 'format=duration',
                            '-of', 'default=noprint_wrappers=1:nokey=1',
                            str(target)], capture_output=True, text=True,
                           check=True, timeout=20)
        final_duration = float(r.stdout.strip())
        if not 30 <= final_duration <= 45:
            raise RuntimeError(f'Locución resultante {final_duration:.1f}s '
                               'fuera del rango 30-45 s')
        scale = final_duration / raw_duration
        approximate = estimate_wordmarks(scenes, ranges)
        marks = [{'text': word['text'],
                  'start': round(word['start'] * scale, 4),
                  'end': round(min(final_duration, word['end'] * scale), 4)}
                 for word in approximate]
        if len(marks) < 40:
            raise RuntimeError('Narración demasiado breve para el Short')
        return marks, final_duration, engine
