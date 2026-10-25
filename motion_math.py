"""ABYSS WILD: deterministic full-frame horizontal camera plans and QA.

All coordinates are output pixels at 1080x1920. The chosen 60–120 px/s is
the peak horizontal speed under smoothstep; endpoints ease to rest.
Horizontal travel needs more than 12% overscan for longer scenes, so scale
is 1.12 + travel / width. This preserves a 12% safety margin *in addition*
to the distance moved, without exposing edges.
"""
import hashlib
import math
from pathlib import Path
import random

import numpy as np
from PIL import Image

W, H = 1080, 1920
CAPTION_Y = 0.52
CAPTION_SAFE_WIDTH = 0.90
MAX_CAPTION_TEXT_PX = 900.0
SIDE_MARGIN = 0.12
MAX_PAN_SPEED = 120.0
MIN_PAN_SPEED = 60.0
ZOOM_LANDSCAPE = 0.02
ZOOM_PORTRAIT = 0.10


def smooth(t):
    t = max(0.0, min(1.0, float(t)))
    return 3 * t * t - 2 * t * t * t


def image_saliency_center(path):
    """Approximate subject focal x,y from edges/contrast (not object recognition).

    A manually supplied focal point in JSON takes priority. The saliency
    heuristic is only used for extremely wide images without explicit focus.
    """
    with Image.open(path) as img:
        sample = img.convert('L')
        sample.thumbnail((360, 180))
        gray = np.asarray(sample, dtype=np.float32) / 255
    if min(gray.shape) < 3:
        return {'x': 0.5, 'y': 0.5}
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    energy = gx + gy
    # Large blurred regions respond to textured/salient areas; avoid edges.
    h, w = energy.shape
    bw = max(8, w // 5)
    bh = max(6, h // 3)
    best = (-1.0, w // 2, h // 2)
    for cy in range(max(1, bh // 2), h, max(1, h // 10)):
        for cx in range(max(1, bw // 2), w, max(1, w // 24)):
            x0, x1 = max(0, cx - bw // 2), min(w, cx + bw // 2)
            y0, y1 = max(0, cy - bh // 2), min(h, cy + bh // 2)
            score = float(np.mean(energy[y0:y1, x0:x1]))
            score *= (1 - 0.14 * abs(cx / w - 0.5))
            if score > best[0]:
                best = (score, cx, cy)
    return {'x': round(max(.08, min(.92, best[1] / w)), 4),
            'y': round(max(.08, min(.92, best[2] / h)), 4)}


def focal_point(source, path=None, aspect=1.0):
    """Prefer a normalized user/AI focal_point in JSON, else heuristic."""
    if isinstance(source, dict):
        x, y = source.get('x'), source.get('y')
        if (type(x) in (float, int) and type(y) in (float, int)
                and math.isfinite(x) and math.isfinite(y)
                and 0 <= x <= 1 and 0 <= y <= 1):
            return {'x': round(float(x), 4), 'y': round(float(y), 4)}
    if aspect > 16 / 9 and path:
        return image_saliency_center(path)
    return {'x': .5, 'y': .5}


def make_camera_plan(beat, pan_number=0, seed='abyss', media_root=None):
    asset = beat.get('asset')
    start, end = float(beat['start']), float(beat['end'])
    seconds = end - start
    if seconds <= 0:
        raise ValueError('Duración inválida de escena para cámara')
    if not asset:
        return {'mode': 'static', 'direction': 'none', 'from_x': 0,
                'to_x': 0, 'base_scale': 1.0, 'zoom_end': 1.0,
                'focal_point': {'x': .5, 'y': .5}, 'speed_px_s': 0}
    width = int(asset.get('width', 0))
    height = int(asset.get('height', 0))
    if width <= 0 or height <= 0:
        raise ValueError('Dimensiones del medio desconocidas')
    aspect = width / height
    media_path = (Path(media_root) / asset['file']
                  if media_root and asset['type'] == 'image' else None)
    point = focal_point(beat.get('focal_point') or asset.get('focal_point'),
                        media_path, aspect)
    if aspect <= 1.0:
        return {'mode': 'zoom', 'direction': 'none', 'from_x': 0,
                'to_x': 0, 'base_scale': 1.0, 'zoom_end': 1.10,
                'focal_point': point, 'speed_px_s': 0}

    digest = hashlib.sha256((str(seed) + '/' + str(beat['beat']) +
                             '/' + str(asset.get('id', ''))).encode()).digest()
    randomizer = random.Random(int.from_bytes(digest[:8], 'big'))
    speed = randomizer.uniform(MIN_PAN_SPEED, MAX_PAN_SPEED)
    direction = 'right' if pan_number % 2 == 0 else 'left'
    sign = 1 if direction == 'right' else -1
    # smoothstep peak slope = 1.5: peak movement speed stays in [60,120].
    travel = (2.0 / 3.0) * speed * seconds
    scale = 1.12 + travel / W
    extra_overscan = SIDE_MARGIN * W / 2
    jitter = randomizer.uniform(-.6, .6) * extra_overscan
    from_x = -sign * travel / 2 + jitter
    to_x = sign * travel / 2 + jitter
    return {'mode': 'pan', 'direction': direction,
            'from_x': round(from_x, 4), 'to_x': round(to_x, 4),
            'base_scale': round(scale, 7), 'zoom_end': 1.02,
            'focal_point': point,
            'speed_px_s': round(speed, 4),
            'wide_crop': aspect > (16 / 9)}


def apply_motion_plans(beats, topic, media_root=None):
    pan_index = 0
    for beat in beats:
        plan = make_camera_plan(beat, pan_index, seed=topic,
                                media_root=media_root)
        beat['camera'] = plan
        if plan['mode'] == 'pan':
            pan_index += 1
    return beats


def validate_motion(beats):
    """Validate metadata and visible coverage at eased sample timestamps.

    Bounding-box proof assumes renderer performs cover-fit into the frame,
    then translateX(px) scale(scale), with transformOrigin=center.
    """
    last_direction = None
    pan_count = 0
    for i, beat in enumerate(beats):
        cam = beat.get('camera')
        if not isinstance(cam, dict):
            raise ValueError(f'Escena {i}: cámara ausente')
        mode = cam.get('mode')
        if mode not in ('pan', 'zoom', 'static'):
            raise ValueError(f'Escena {i}: modo de cámara inválido')
        if mode == 'pan':
            direction = cam['direction']
            expected = 'right' if pan_count % 2 == 0 else 'left'
            if direction != expected or direction == last_direction:
                raise ValueError(f'Escena {i}: dirección horizontal no alterna')
            last_direction = direction
            pan_count += 1
            seconds = beat['end'] - beat['start']
            speed = 1.5 * abs(cam['to_x'] - cam['from_x']) / seconds
            if not 60 - .02 <= speed <= 120 + .02:
                raise ValueError(f'Escena {i}: velocidad fuera de 60–120 px/s')
            if not 1.0 <= cam['zoom_end'] <= 1.02:
                raise ValueError(f'Escena {i}: zoom horizontal >2%')
            if cam['base_scale'] < 1.12:
                raise ValueError(f'Escena {i}: no tiene 12% de sobreescala')
        else:
            if cam['direction'] != 'none' or cam['from_x'] != 0 or cam['to_x'] != 0:
                raise ValueError(f'Escena {i}: paneo en modo estático/zoom')
            if mode == 'zoom' and not 1.0 <= cam['zoom_end'] <= 1.10:
                raise ValueError(f'Escena {i}: zoom vertical/cuadrado >10%')
        focal = cam.get('focal_point')
        if not isinstance(focal, dict) or not all(
                isinstance(focal.get(dim), (float, int)) and
                math.isfinite(focal[dim]) and 0 <= focal[dim] <= 1
                for dim in ('x', 'y')):
            raise ValueError(f'Escena {i}: punto de interés inválido')
        for time in [j / 40 for j in range(41)]:
            offset = cam['from_x'] + (cam['to_x'] - cam['from_x']) * smooth(time)
            scale = cam['base_scale'] * (
                1 + (cam['zoom_end'] - 1) * smooth(time))
            if scale * W / 2 - abs(offset) < W / 2 - .1:
                raise ValueError(f'Escena {i}: borde horizontal vacío')
            if scale * H / 2 < H / 2 - .1:
                raise ValueError(f'Escena {i}: borde vertical vacío')
    return pan_count


def validate_captions(captions, layout):
    if layout != {'y': CAPTION_Y, 'max_width': CAPTION_SAFE_WIDTH,
                  'max_text_px': MAX_CAPTION_TEXT_PX}:
        raise ValueError('Subtítulos fuera de la zona media segura')
    for i, caption in enumerate(captions):
        words = caption.get('words')
        if not isinstance(words, list) or len(words) != 1:
            raise ValueError(f'Subtítulo {i} no es una sola palabra')
        word = words[0].get('text', '')
        if not isinstance(word, str) or not word.strip():
            raise ValueError(f'Subtítulo {i} vacío')
        # The renderer uses textLength <=900 within a 972px SVG safe field.
        if MAX_CAPTION_TEXT_PX + 12 > W * CAPTION_SAFE_WIDTH:
            raise ValueError('Tipografía rebasa 90% de ancho por trazo')
    return len(captions)
