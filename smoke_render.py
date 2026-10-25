"""Secret-free end-to-end Remotion smoke fixture for GitHub Actions CI.

Not published. Uses artificial footage only to validate full-frame video
playback, one-word captions and mascot overlay with a real headless render.
"""
import json
import subprocess
from pathlib import Path
from viral_visuals import make_mascots

ROOT = Path(__file__).resolve().parent
public = ROOT/'render'/'public'
media = public/'media'
work = ROOT/'work'
media.mkdir(parents=True,exist_ok=True)
work.mkdir(parents=True,exist_ok=True)
clip = media/'smoke_broll.mp4'
subprocess.run(
    ['ffmpeg','-hide_banner','-loglevel','error','-y',
     '-f','lavfi','-i','testsrc2=size=1080x1920:rate=30:duration=3.5',
     '-an','-c:v','libx264','-preset','ultrafast','-crf','27',
     '-pix_fmt','yuv420p',str(clip)],check=True)
make_mascots(media)
data = {
    'topic':'Prueba visual', 'duration':3.5,'fps':30,
    'beats':[{'beat':0,'start':0,'end':3.5,
              'asset':{'type':'video','file':'smoke_broll.mp4',
                       'width':1080,'height':1920}}],
    'captions':[
        {'start':.18,'end':.77,'words':[{'text':'TITANOBOA','start':.18,'end':.77}]},
        {'start':.85,'end':1.45,'words':[{'text':'GIGANTE','start':.85,'end':1.45}]},
        {'start':1.5,'end':2.1,'words':[{'text':'COLOMBIA','start':1.5,'end':2.1}]}
    ],
    'caption_layout':{'y':.5,'max_width':.9,'max_text_px':900},
    'mascots':[{'start':0,'end':3,'file':'mascot_surprised.png'}]
}
(public/'data.json').write_text(json.dumps(data),encoding='utf-8')
print('Headless 3.5s B-roll + captions + avatar fixture ready')
