import test from 'node:test';
import assert from 'node:assert/strict';
import {W, H, CAPTION_TOP, CAPTION_WIDTH, MAX_TEXT_PX,
  smoothstep, motionAt, frameCoverage, focalCSS, captionWidthPx}
  from '../src/motion.js';

const camera = {
  mode: 'pan', direction: 'right', from_x: -120, to_x: 130,
  base_scale: 1.41, zoom_end: 1.02, focal_point: {x: .75, y: .41},
  speed_px_s: 100,
};

test('smoothstep eases and stays monotonic', () => {
  assert.equal(smoothstep(0), 0);
  assert.equal(smoothstep(.5), .5);
  assert.equal(smoothstep(1), 1);
  let prev = 0;
  for (let i=0; i<=100; i++) {
    const x = smoothstep(i/100);
    assert.ok(x>=prev);
    prev=x;
  }
});

test('camera is horizontal-only, fully covered throughout zoom', () => {
  for (let i=0; i<=100; i++) {
    const t = i/100;
    const m = motionAt(camera, t);
    assert.equal(m.y, 0);
    const borders=frameCoverage(camera, t);
    assert.ok(borders.horizontal && borders.vertical);
  }
  assert.ok(motionAt(camera,0).x < motionAt(camera,1).x);
});

test('focal point is normalized subject ROI', () => {
  assert.equal(focalCSS({x:.8,y:.25}), '80% 25%');
  assert.equal(focalCSS({x:2,y:-1}), '100% 0%');
  // A panoramic image must place its focal point near the screen center
  // rather than the outer 80% of the visible frame.
  const wide={width:3100,height:1050};
  const [px,py]=focalCSS({x:.8,y:.25},wide).split(' ').map(parseFloat);
  const scaledWidth=wide.width*1920/wide.height;
  const focalScreenX=.8*scaledWidth + (px/100)*(1080-scaledWidth);
  assert.ok(Math.abs(focalScreenX-540)<.01);
  assert.equal(py,50);
});

test('caption always fits width and anchors to midframe', () => {
  assert.equal(CAPTION_TOP, .52);
  assert.equal(CAPTION_WIDTH, .9);
  assert.equal(W * CAPTION_WIDTH, 972);
  assert.ok(MAX_TEXT_PX <= 900);
  for (const word of ['Y', 'TITANOBOA', 'ELECTROENCEFALOGRAFISTA', 'W'.repeat(90)]) {
    const textLength = captionWidthPx(word);
    assert.ok(textLength>=90 && textLength<=900);
    // SVG stroke 12px and pulse <=2%; bound below 90% of full frame.
    assert.ok(textLength*1.025 + 12 < 972);
  }
});

test('zoom-only vertical media stays covered at all frames', () => {
  const zoom = {mode: 'zoom', from_x:0,to_x:0,
    base_scale:1,zoom_end:1.1, focal_point:{x:.5,y:.5}};
  for(let i=0; i<=100; i++) {
    assert.ok(frameCoverage(zoom,i/100).horizontal);
    assert.ok(frameCoverage(zoom,i/100).vertical);
  }
});
