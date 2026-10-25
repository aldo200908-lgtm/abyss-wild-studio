import React from 'react';
import {registerRoot, Composition, AbsoluteFill, Img, OffthreadVideo,
  Sequence, staticFile, useCurrentFrame, useVideoConfig, spring} from 'remotion';
import '@fontsource/anton/400.css';
import data from '../public/data.json';
import {motionAt, focalCSS, captionWidthPx, CAPTION_TOP, CAPTION_WIDTH}
  from './motion.js';

const BG = ['#051c2a', '#0f1730', '#19243b', '#0e302d', '#25203b', '#14263b'];
const FPS = 30;

const Letter = ({children, style = {}}) => (
  <div style={{fontFamily: 'Anton, Impact, sans-serif',
    textTransform: 'uppercase', letterSpacing: 1.4, ...style}}>{children}</div>
);

const SizeBar = ({length, progress}) => {
  if (typeof length !== 'number' || length <= 0) return null;
  return <div style={{position: 'absolute', top: 690, left: '10%', width: '80%',
    padding: 24, border: '3px solid #ffd347', borderRadius: 18,
    background: '#06111bb8'}}>
    <Letter style={{fontSize: 40, color: '#ffe47a', textAlign: 'center'}}>
      COMPARACIÓN DE TAMAÑO
    </Letter>
    <div style={{marginTop: 25, background: '#253b49', height: 35,
      borderRadius: 10}}>
      <div style={{background: '#f9c527', width: (progress * 95) + '%',
        height: '100%', borderRadius: 10}}/>
    </div>
    <Letter style={{fontSize: 65, color: 'white',
      textAlign: 'right'}}>{length} m</Letter>
  </div>;
};

const Scene = ({item}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const durationFrames = Math.max(1, Math.round((item.end - item.start) * fps));
  const progress = Math.min(1, frame / Math.max(1, durationFrames - 1));
  const reveal = spring({frame, fps, config: {damping: 14, stiffness: 130}});
  const camera = item.camera;
  const {x, scale} = motionAt(camera, progress);
  const bg = BG[item.beat % BG.length];
  const visual = item.asset;
  const objectPosition = focalCSS(camera.focal_point, visual);

  // CSS order is intentional: translate output pixels AFTER cover-image scale.
  // The renderer's media element first covers the 1080x1920 viewport.
  const transform = 'translateX(' + x + 'px) scale(' + scale + ')';

  return <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
    <AbsoluteFill style={{transform, transformOrigin: '50% 50%', overflow: 'hidden'}}>
      {visual?.type === 'image' &&
        <Img src={staticFile('media/' + visual.file)}
          style={{width: '100%', height: '100%', objectFit: 'cover',
            objectPosition, display: 'block'}} />}
      {visual?.type === 'video' &&
        <OffthreadVideo src={staticFile('media/' + visual.file)} muted
          style={{width: '100%', height: '100%', objectFit: 'cover',
            objectPosition, display: 'block'}} />}
      {!visual && <>
        <div style={{position: 'absolute', top: 200, left: -100,
          width: 1100, height: 900, border: '24px solid #57b6bc33',
          borderRadius: '50%', transform: 'rotate(' + (frame / 12) + 'deg)'}}/>
        <div style={{position: 'absolute', top: 470, right: -180,
          width: 600, height: 600, border: '12px solid #ffd44733',
          transform: 'rotate(' + (25 + frame * .25) + 'deg)'}}/>
        <Letter style={{position: 'absolute', top: 480, left: 110, right: 110,
          fontSize: 78, lineHeight: 1.2, textAlign: 'center', color: '#f5f7f8',
          textShadow: '0 5px 20px #0009',
          transform: 'translateY(' + ((1 - reveal) * 85) + 'px)'}}>
          {item.line}
        </Letter>
      </>}
    </AbsoluteFill>
    <AbsoluteFill style={{background:
      'linear-gradient(180deg, #000b 0%, transparent 28%, #0002 50%, #000c 100%)'}} />
    <div style={{position: 'absolute', top: 145, left: 85, right: 85,
      display: 'flex', alignItems: 'center', gap: 16}}>
      <div style={{width: 16, height: 16, background: '#ffd447',
        borderRadius: '50%'}}/>
      <Letter style={{fontSize: 43, color: '#fff'}}>{data.topic}</Letter>
    </div>
    <div style={{position: 'absolute', top: 264, left: 85,
      maxWidth: 910, background: '#06111bdc', padding: '13px 25px',
      borderLeft: '8px solid #ffd447', borderRadius: 8,
      transform: 'scale(' + (.84 + .16 * reveal) + ')',
      transformOrigin: 'left center'}}>
      <Letter style={{fontSize: 28, color: '#e8f2f4'}}>
        {item.label || 'DATO VERIFICADO'}
      </Letter>
    </div>
    <SizeBar length={item.compare_m} progress={reveal} />
    <div style={{position: 'absolute', top: 1735, left: 88, right: 88,
      height: 8, borderRadius: 30, background: '#ffffff30'}}>
      <div style={{height: '100%', borderRadius: 30, background: '#ffd447',
        width: (100 * Math.min(1, Math.max(0, item.end / data.duration))) + '%'}}/>
    </div>
  </AbsoluteFill>;
};

const Captions = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const seconds = frame / fps;
  const cue = data.captions.find(c => seconds >= c.start && seconds <= c.end + .035);
  if (!cue || cue.words?.length !== 1) return null;
  const word = cue.words[0].text;
  const active = seconds >= cue.words[0].start && seconds <= cue.words[0].end;
  const pulse = spring({frame: Math.max(0, frame - Math.round(cue.start * fps)),
    fps, config: {damping: 11, mass: .8, stiffness: 260}});
  const scale = active ? .99 + .025 * pulse : 1;
  // Fixed 972px SVG viewport with textLength <=900px (plus 12px outline).
  // Exact horizontal centering at x=486, no line wrapping, no lower-third captions.
  return <div style={{position: 'absolute', top: (CAPTION_TOP * 100) + '%',
    left: ((1 - CAPTION_WIDTH) * 50) + '%', width: (CAPTION_WIDTH * 100) + '%',
    height: 200, transform: 'translateY(-50%)', zIndex: 30,
    display: 'flex', justifyContent: 'center', alignItems: 'center',
    pointerEvents: 'none'}}>
    <svg viewBox="0 0 972 200" width="100%" height="100%"
      preserveAspectRatio="xMidYMid meet" style={{overflow: 'visible'}}>
      <text x="486" y="100" textAnchor="middle" dominantBaseline="middle"
        textLength={captionWidthPx(word)} lengthAdjust="spacingAndGlyphs"
        fontFamily="Anton, Impact, sans-serif" fontSize="112"
        fill={active ? '#ffdf26' : 'white'} stroke="#0b0b0c"
        strokeWidth="12" strokeLinejoin="round" paintOrder="stroke fill"
        style={{textTransform: 'uppercase',
          transform: 'scale(' + scale + ')',
          transformOrigin: '486px 100px'}}>
        {word}
      </text>
    </svg>
  </div>;
};

const Video = () => <AbsoluteFill style={{background: '#05151f'}}>
  {data.beats.map(beat => <Sequence key={beat.beat}
    from={Math.round(beat.start * FPS)}
    durationInFrames={Math.max(1, Math.round(beat.end * FPS) -
      Math.round(beat.start * FPS))}>
    <Scene item={beat}/>
  </Sequence>)}
  <Captions />
</AbsoluteFill>;

const Root = () => <Composition id="Short" component={Video}
  durationInFrames={Math.ceil(data.duration * FPS)} fps={FPS}
  width={1080} height={1920}/>;

registerRoot(Root);
