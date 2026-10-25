// Shared Remotion camera geometry; verified by Node tests.
// Matches motion_math.py: smoothstep(t), translateX in output pixels, cover-fit.
export const W = 1080;
export const H = 1920;
export const CAPTION_TOP = 0.52;
export const CAPTION_WIDTH = 0.90;
export const MAX_TEXT_PX = 900;

export const smoothstep = (t) => {
  const x = Math.max(0, Math.min(1, Number.isFinite(t) ? t : 0));
  return x * x * (3 - 2 * x);
};

export const motionAt = (camera, progress) => {
  const t = smoothstep(progress);
  return {
    x: camera.from_x + (camera.to_x - camera.from_x) * t,
    y: 0,
    scale: camera.base_scale * (1 + (camera.zoom_end - 1) * t),
  };
};

export const frameCoverage = (camera, progress) => {
  const {x, scale} = motionAt(camera, progress);
  return {
    horizontal: scale * W / 2 - Math.abs(x) >= W / 2 - 0.1,
    vertical: scale * H / 2 >= H / 2 - 0.1,
  };
};

export const focalCSS = (point = {x: 0.5, y: 0.5}) => {
  const x = Math.max(0, Math.min(1, Number(point?.x ?? 0.5)));
  const y = Math.max(0, Math.min(1, Number(point?.y ?? 0.5)));
  return (x * 100) + '% ' + (y * 100) + '%';
};

export const captionWidthPx = (word) =>
  Math.min(MAX_TEXT_PX, Math.max(90, [...String(word)].length * 59));
