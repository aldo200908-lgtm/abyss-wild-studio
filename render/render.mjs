import {bundle} from '@remotion/bundler';
import {ensureBrowser, renderMedia, selectComposition} from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const here = import.meta.dirname;
const output = path.resolve(here, '..', 'work');
fs.mkdirSync(output, {recursive: true});
const start = Date.now();
await ensureBrowser();
const serveUrl = await bundle({entryPoint: path.join(here, 'src', 'index.jsx')});
const composition = await selectComposition({serveUrl, id: 'Short'});
let last = -1;
await renderMedia({serveUrl, composition, codec: 'h264', outputLocation: path.join(output, 'silent.mp4'),
  crf: 22, concurrency: 2, pixelFormat: 'yuv420p',
  onProgress: ({progress}) => {
    const pct = Math.floor(progress * 10);
    if (pct !== last) { last = pct; console.log(`[RENDER] ${pct * 10}%`); }
  }});
const seconds = Math.round((Date.now() - start) / 1000);
fs.writeFileSync(path.join(output, 'render_stats.json'), JSON.stringify({render_seconds: seconds}));
console.log(`[RENDER] Completed in ${seconds}s`);
