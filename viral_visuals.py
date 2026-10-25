"""ABYSS WILD: fail-closed fullscreen B-roll, Ken Burns and transparent mascot.

FFmpeg renders each approved image with zoompan, 1080x1920 @ 30 fps.
Source footage is cropped to the same portrait resolution. No typographic
placeholder, black card or empty background is ever accepted.
"""
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageStat, ImageOps

W, H, FPS = 1080, 1920, 30
MIN_SHOT = 3.0
MAX_SHOT = 4.0


def shot_ranges(duration):
    """All shots last 3–4s for normal 30–45s Shorts."""
    duration = float(duration)
    count = math.ceil(duration / MAX_SHOT)
    if count < 1 or duration / count < MIN_SHOT - .01:
        raise ValueError('Duración incompatible con cambios de imagen de 3–4s')
    return [(round(duration*i/count, 4), round(duration*(i+1)/count, 4))
            for i in range(count)]


def image_ok(path):
    """Reject blank, uniform, tiny or broken files before rendering."""
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        if min(im.size) < 300:
            return False
        thumb = ImageOps.exif_transpose(im).convert('RGB')
        thumb.thumbnail((180, 180))
        stats = ImageStat.Stat(thumb)
        return max(stats.stddev) >= 9 and max(stats.extrema[i][1] - stats.extrema[i][0]
                                               for i in range(3)) > 38


def run_ffmpeg(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Error FFmpeg: ' + result.stderr[-1600:])


def prepare_image(src, dest, seconds, motion_index):
    """FFmpeg zoompan operates on a properly covered 9:16 still.

    zoompan always crops inside the full image at z >= 1, preventing borders.
    Modes: zoom in, zoom out, pan right, pan left.
    """
    src, dest = Path(src), Path(dest)
    if not image_ok(src):
        raise ValueError('Imagen vacía, corrupta o demasiado pequeña')
    dest.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, round(seconds * FPS))
    last = max(1, frames - 1)
    mode = motion_index % 4
    progress = f'(on/{last})'
    if mode == 0:
        z = f'1.0+0.15*{progress}'
        x = '(iw-iw/zoom)/2'
    elif mode == 1:
        z = f'1.15-0.15*{progress}'
        x = '(iw-iw/zoom)/2'
    elif mode == 2:
        z = '1.15'
        x = f'(iw-iw/zoom)*{progress}'
    else:
        z = '1.15'
        x = f'(iw-iw/zoom)*(1-{progress})'
    # source image is first center/focal cropped to exactly 9:16 with Pillow,
    # then FFmpeg zoompan guarantees a filled output frame at every timestamp.
    with Image.open(src) as opened:
        opened = ImageOps.exif_transpose(opened).convert('RGB')
        cover = ImageOps.fit(opened, (W, H), method=Image.Resampling.LANCZOS)
        tmp = dest.with_name(dest.stem + '_source.jpg')
        cover.save(tmp, 'JPEG', quality=93)
    filt = (f"zoompan=z='{z}':x='{x}':y='(ih-ih/zoom)/2':"
            f"d={frames}:s={W}x{H}:fps={FPS},"
            f"trim=duration={seconds:.5f},setsar=1,"
            "format=yuv420p")
    try:
        run_ffmpeg(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-loop', '1', '-framerate', str(FPS), '-i', str(tmp),
                    '-vf', filt, '-frames:v', str(frames), '-an', '-c:v', 'libx264',
                    '-preset', 'veryfast', '-crf', '22', '-movflags', '+faststart',
                    str(dest)])
    finally:
        tmp.unlink(missing_ok=True)
    verify_video(dest, seconds)


def prepare_video(src, dest, seconds, motion_index):
    src, dest = Path(src), Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, round(seconds * FPS))
    # Smooth crop from real video; never stretch 16:9 footage.
    pan = ('(in_w-out_w)*t/{:.5f}'.format(seconds) if motion_index % 2 == 0
           else '(in_w-out_w)*(1-t/{:.5f})'.format(seconds))
    # Crop expression uses frame counter because crop's x expression does not
    # consistently support t across all FFmpeg versions.
    pan = ('(in_w-out_w)*n/{}'.format(max(1, frames-1)) if motion_index % 2 == 0
           else '(in_w-out_w)*(1-n/{})'.format(max(1, frames-1)))
    vf = (f'fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase,'
          f"crop={W}:{H}:x='{pan}':y='(in_h-out_h)/2',"
          'setsar=1,format=yuv420p')
    run_ffmpeg(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                '-stream_loop', '-1', '-i', str(src), '-t', str(seconds),
                '-vf', vf, '-frames:v', str(frames),
                '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '22',
                '-movflags', '+faststart', str(dest)])
    verify_video(dest, seconds)


def verify_video(path, expected):
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
                            '-show_entries', 'stream=width,height,nb_frames',
                            '-of', 'csv=p=0', str(path)],
                           capture_output=True, text=True, check=True).stdout.strip()
    fields = probe.split(',')
    if len(fields) < 2 or fields[:2] != [str(W), str(H)]:
        raise RuntimeError('Plano B-roll no cubre 1080x1920: ' + str(path))
    if not path.exists() or path.stat().st_size < 10000:
        raise RuntimeError('Plano B-roll vacío: ' + str(path))
    # Check representative frames, including beginning and final beat.
    for at in (0, max(0, expected/2), max(0, expected-.13)):
        result = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{at:.3f}',
                                 '-i', str(path), '-frames:v', '1', '-vf',
                                 'scale=96:170', '-f', 'rawvideo', '-pix_fmt',
                                 'rgb24', '-'], capture_output=True, check=True)
        from io import BytesIO
        if len(result.stdout) != 96*170*3:
            raise RuntimeError('Fotograma faltante en ' + str(path))
        im = Image.frombytes('RGB', (96, 170), result.stdout)
        if max(ImageStat.Stat(im).stddev) < 5:
            raise RuntimeError('Fotograma plano/negro en ' + str(path))


def make_mascots(dest):
    """Original reusable transparent sea-creature PNG expressions, no GUI."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    result = []
    scale = 2
    for mood in ('surprised', 'thinking', 'happy'):
        im = Image.new('RGBA', (440*scale, 520*scale), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        q = lambda x: round(x*scale)
        rect = lambda box, fill, radius: d.rounded_rectangle(
            tuple(q(v) for v in box), radius=q(radius), fill=fill)
        ell = lambda box, fill, outline=None, width=1: d.ellipse(
            tuple(q(v) for v in box), fill=fill, outline=outline,
            width=q(width))
        # Tentacles, body, glow rim and deep-ocean highlights.
        for x, y in ((62,365),(122,410),(240,412),(334,360)):
            ell((x, y, x+86, y+65), '#0a839e')
        ell((46,65,396,430), '#065e7a')
        ell((56,80,382,417), '#0c9bb1')
        ell((88,105,345,338), '#24c6cd')
        ell((112,105,178,154), '#a2ffff')
        ell((300,165,327,196), '#a2ffff')
        # Emotive, high-contrast face.
        for x in (138,278):
            ell((x-35,206,x+35,286), '#f7fdff')
            ell((x-17,226,x+17,274), '#10263b')
            ell((x-9,230,x+1,242), '#ffffff')
        if mood == 'surprised':
            ell((194,293,246,355), '#11263b')
        elif mood == 'thinking':
            d.arc(tuple(q(v) for v in (185,300,255,348)), 0, 180,
                  fill='#11263b', width=q(10))
            rect((345,287,391,312), '#19adba', 22)
        else:
            d.arc(tuple(q(v) for v in (175,275,263,354)), 5, 175,
                  fill='#11263b', width=q(12))
            for x in (115,310):
                ell((x-22,295,x+16,315), '#f5839a')
        file = dest / f'mascot_{mood}.png'
        im.resize((440,520), Image.Resampling.LANCZOS).save(file)
        with Image.open(file) as check:
            if check.mode != 'RGBA' or check.getextrema()[3][0] != 0:
                raise RuntimeError('PNG mascota no transparente')
        result.append(file.name)
    return result


def mascot_events(duration):
    points = [(0.0, 3.0, 'surprised'),
              (duration*.36, 4.0, 'thinking'),
              (duration*.73, 4.0, 'happy')]
    return [{'start': round(start,3),
             'end': round(min(duration,start+length),3),
             'file': f'mascot_{mood}.png'} for start,length,mood in points
            if start < duration]
