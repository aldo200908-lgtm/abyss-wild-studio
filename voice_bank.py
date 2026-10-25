"""Generate 5 numbered previews; hard-fail if a requested Azure es-* voice fails.

Piper Spanish is an OPTIONAL reference only; never selected in the
production workflow and never used to conceal Azure errors.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile
from native_spanish_voice import (AzureSpanishSpeech, VOICES, config_from)
from spanish_voice_text import load_dictionary, normalizar, fonetizar


def create_bank(directory, phrase, include_piper=False):
    cfg = config_from('config.json')
    dictionary = load_dictionary('pronunciacion.json')
    phrase = fonetizar(normalizar(phrase), dictionary)
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    speaker = AzureSpanishSpeech(os.getenv('AZURE_SPEECH_KEY'),
                                 os.getenv('AZURE_SPEECH_REGION'))
    count = 0
    for count, voice in enumerate(VOICES, 1):
        locale = speaker.ensure_voice(voice)
        with tempfile.TemporaryDirectory() as tempdir:
            wav = Path(tempdir) / 'voice.wav'
            speaker.synthesize(phrase, wav, voice, cfg['rate_percent'])
            mp3 = folder / f'{count:02d}_{voice}.mp3'
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error',
                            '-y', '-i', str(wav), '-codec:a', 'libmp3lame',
                            '-q:a', '3', str(mp3)], check=True)
        (folder / f'{count:02d}_{voice}_info.txt').write_text(
            f'{count:02d} — {voice}\nLocale validado: {locale}\n'
            'Proveedor: Microsoft Azure Speech\n'
            f'Velocidad: {cfg["rate_percent"]}%\n'
            f'Texto narrado: {phrase}\n', encoding='utf-8')
    if include_piper:
        from offline_voice import piper_engine, write_scene_audio
        try:
            piper = piper_engine()
            with tempfile.TemporaryDirectory() as tmp:
                wave = write_scene_audio([{'line': phrase}], tmp,
                                         'Piper', piper)[0]
                # The offline voice is a separate comparison sample, never a fallback.
                source = Path(tmp) / 'scene_00.wav'
                mp3 = folder / '06_es-MX-PiperAld_opcional.mp3'
                subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error',
                                '-y', '-i', str(source), '-codec:a', 'libmp3lame',
                                '-q:a', '3', str(mp3)], check=True)
                (folder / '06_es-MX-PiperAld_opcional_info.txt').write_text(
                    '06 — es-MX-PiperAld (comparación CPU, no Azure)\n'
                    'Locale del modelo: es-MX\nNo se utiliza como fallback.\n'
                    f'Texto narrado: {phrase}\n', encoding='utf-8')
        except Exception as exc:
            (folder / '06_es-MX-Piper_error.txt').write_text(
                f'Piper opcional no pudo producir muestra: {type(exc).__name__}\n',
                encoding='utf-8')
    archive = folder.parent / 'banco_voces_espanolas.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as dest:
        for file in sorted(folder.iterdir()):
            dest.write(file, file.name)
    if count != len(VOICES):
        raise RuntimeError('Banco de voces incompleto; no se publicó ZIP parcial')
    print('BANCO_LISTO:', archive)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phrase', default=None)
    parser.add_argument('--include-piper', action='store_true')
    args = parser.parse_args()
    config = config_from('config.json')
    create_bank('work/voice_bank', args.phrase or config['bank_test_phrase'],
                args.include_piper)
