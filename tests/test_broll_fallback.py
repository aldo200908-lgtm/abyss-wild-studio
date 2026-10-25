"""Reproduce Short #14: Paleocene scene without its own B-roll result.

A verified Titanoboa image may be re-audited and reused as contextual
illustration. Reject the same image if that scene-specific audit says no.
"""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

import pipeline
from broll_search import search_terms, reorder_fallback_assets


def artificial_jpeg():
    im = Image.new('RGB', (900, 1500), '#193948')
    draw = ImageDraw.Draw(im)
    for x in range(0, 900, 60):
        draw.rectangle((x, 0, x+28, 1499), fill=(34+x//7, 80+x//15, 120))
    draw.ellipse((160, 410, 760, 1190), fill='#b59348')
    out = io.BytesIO()
    im.save(out, format='JPEG', quality=91)
    return out.getvalue()


def example_script():
    n=9
    seconds=36
    timeline=[]
    for i in range(n):
        line = ('Este género de serpiente gigante vivió en el Paleoceno.'
                if i == 1 else 'Titanoboa, serpiente fósil de Colombia.')
        timeline.append({'start':i*4.,'end':(i+1)*4.,
                         'line':line, 'visual_type':'reconstruction',
                         'visual_query': 'Titanoboa fossil' if i==0
                                         else 'Paleocene forest reconstruction'})
    return {'topic':'Titanoboa','duration':seconds,'timeline':timeline,
            'captions':[]}


class BrollFallbackTests(unittest.TestCase):
    def test_paleocene_has_specific_research_terms(self):
        line={'line':'Este género de serpiente gigante vivió en el Paleoceno.',
              'visual_query':'Paleoceno'}
        terms=search_terms('Titanoboa',line)
        self.assertIn('Titanoboa',terms)
        self.assertIn('Paleocene rainforest reconstruction',terms)
        self.assertGreater(len(terms),3)

    def test_fallback_checks_nearest_relevant_media(self):
        rows=[{'scene_index':0},{'scene_index':4},{'scene_index':9}]
        self.assertEqual([r['scene_index'] for r in
                          reorder_fallback_assets(rows,5)],[4,9,0])

    def _run_selection(self, approve):
        candidate={'type':'image','id':'File:Titanoboa scientific model.jpg',
                   'preview':'https://upload.wikimedia.org/test.jpg',
                   'download':'https://upload.wikimedia.org/test.jpg',
                   'title':'Titanoboa model','license':'CC BY-SA 4.0',
                   'author':'Archivo documental','license_url':'https://creativecommons.org/licenses/by-sa/4.0/',
                   'page':'https://commons.wikimedia.org/wiki/File:Titanoboa',
                   }
        raw=artificial_jpeg()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            media=root/'media'; media.mkdir()
            public=root/'public'; public.mkdir()
            work=root/'work'; work.mkdir()
            def fake_shot(src,dest,length,index,focal=None):
                # The format is separately verified in FFmpeg smoke tests.
                dest.write_bytes(b'x'*12000)
            with patch.object(pipeline,'MEDIA',media), \
                 patch.object(pipeline,'PUBLIC',public), \
                 patch.object(pipeline,'WORK',work), \
                 patch.object(pipeline,'Gemini'), \
                 patch.object(pipeline,'commons_candidates',
                              side_effect=lambda q: [candidate] if q=='Titanoboa'
                              else []), \
                 patch.object(pipeline,'pexels_candidates',return_value=[]), \
                 patch.object(pipeline,'fetch_bytes',return_value=raw), \
                 patch.object(pipeline,'approve_visual',side_effect=approve), \
                 patch.object(pipeline,'prepare_image',side_effect=fake_shot), \
                 patch.object(pipeline,'make_mascots',return_value=[]):
                document=example_script()
                pipeline.choose_assets(document)
                return document, pipeline.load_json(public/'data.json')

    def test_short_14_paleocene_uses_approved_source_no_blank_cards(self):
        document, data=self._run_selection(
            lambda gemini,scene,candidate,preview:
                {'match':True,'focal_point':{'x':.5,'y':.5}})
        self.assertEqual(document['broll_beats'],9)
        self.assertEqual(document['broll_unique_sources'],1)
        self.assertGreaterEqual(document['broll_reused_scenes'],1)
        self.assertIn(2,document['credits'][0]['scenes_used'])
        self.assertTrue(all(beat['asset']['file'].endswith('.mp4')
                            for beat in data['beats']))
        self.assertTrue(any(beat['contextual_reuse'] for beat in data['beats']))
        self.assertTrue(all(3 <= beat['end']-beat['start'] <= 4.01
                            for beat in data['beats']))

    def test_inappropriate_earlier_media_cannot_bypass_audit(self):
        def audit(gemini,scene,candidate,preview):
            return {'match':True} if 'Paleoceno' not in scene['line'] else None
        with self.assertRaisesRegex(RuntimeError, 'Sin B-roll adecuado'):
            self._run_selection(audit)


if __name__ == '__main__':
    unittest.main()
