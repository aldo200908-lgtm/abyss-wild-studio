import React from 'react';
import {registerRoot, Composition, AbsoluteFill, Img, OffthreadVideo,
  Sequence, staticFile, useCurrentFrame, useVideoConfig, interpolate, spring} from 'remotion';
import '@fontsource/anton/400.css';
import data from '../public/data.json';

const BG = ['#051c2a', '#0f1730', '#19243b', '#0e302d', '#25203b', '#14263b'];
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

const Letter = ({children, style = {}}) => (
  <div style={{fontFamily: 'Anton, Impact, sans-serif', textTransform: 'uppercase',
    letterSpacing: 1.4, ...style}}>{children}</div>
);

const SizeBar = ({length, progress}) => {
  if (!length || typeof length !== 'number' || length <= 0) return null;
  return <div style={{position: 'absolute', top: 690, left: '10%', width: '80%',
    padding: 24, border: '3px solid #ffd347', borderRadius: 18, background: '#06111bb8'}}>
    <Letter style={{fontSize: 40, color: '#ffe47a', textAlign: 'center'}}>COMPARACIÓN DE TAMAÑO</Letter>
    <div style={{marginTop: 25, background: '#253b49', height: 35, borderRadius: 10}}>
      <div style={{background: '#f9c527', width: `${progress * 95}%`, height: '100%', borderRadius: 10}} />
    </div>
    <Letter style={{fontSize: 65, color: 'white', textAlign: 'right'}}>{length} m</Letter>
  </div>;
};

const Scene = ({item}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const reveal = spring({frame, fps, config: {damping: 14, stiffness: 130}});
  const duration = Math.max(1, Math.round((item.end - item.start) * fps));
  const zoom = interpolate(frame, [0, duration], [1.035, 1.10], clamp);
  const pan = Math.sin((item.beat % 2 ? -1 : 1) * frame / 36) * 24;
  const bg = BG[item.beat % BG.length];
  const visual = item.asset;
  return <AbsoluteFill style={{background: bg, overflow: 'hidden'}}>
    <AbsoluteFill style={{transform: `scale(${zoom}) translateX(${pan}px)`}}>
      {visual?.type === 'image' &&
        <Img src={staticFile(`media/${visual.file}`)}
          style={{width: '100%', height: '100%', objectFit: 'cover'}} />}
      {visual?.type === 'video' &&
        <OffthreadVideo src={staticFile(`media/${visual.file}`)} muted
          style={{width: '100%', height: '100%', objectFit: 'cover'}} />}
      {!visual && <>
        <div style={{position: 'absolute', top: 200, left: -100, width: 1100, height: 900,
          border: '24px solid #57b6bc33', borderRadius: '50%', transform: `rotate(${frame}deg)`}}/>
        <div style={{position: 'absolute', top: 470, right: -180, width: 600, height: 600,
          border: '12px solid #ffd44733', transform: `rotate(${25 + frame * .5}deg)`}}/>
        <Letter style={{position: 'absolute', top: 480, left: 110, right: 110, fontSize: 78,
          lineHeight: 1.2, textAlign: 'center', color: '#f5f7f8',
          textShadow: '0 5px 20px #0009', transform: `translateY(${(1 - reveal) * 85}px)`}}>
          {item.line}
        </Letter>
      </>}
    </AbsoluteFill>
    <AbsoluteFill style={{background: 'linear-gradient(180deg, #000b 0%, transparent 28%, #0002 50%, #000c 100%)'}} />
    <div style={{position: 'absolute', top: 145, left: 85, right: 85,
      display: 'flex', alignItems: 'center', gap: 16}}>
      <div style={{width: 16, height: 16, background: '#ffd447', borderRadius: '50%'}} />
      <Letter style={{fontSize: 43, color: '#fff'}}>{data.topic}</Letter>
    </div>
    <div style={{position: 'absolute', top: 264, left: 85, maxWidth: 910,
      background: '#06111bdc', padding: '13px 25px', borderLeft: '8px solid #ffd447',
      borderRadius: 8, transform: `scale(${.84 + .16 * reveal})`, transformOrigin: 'left center'}}>
      <Letter style={{fontSize: 28, color: '#e8f2f4'}}>{item.label || 'DATO VERIFICADO'}</Letter>
    </div>
    <SizeBar length={item.compare_m} progress={reveal} />
    <div style={{position: 'absolute', top: 1735, left: 88, right: 88, height: 8,
      borderRadius: 30, background: '#ffffff30'}}>
      <div style={{height: '100%', borderRadius: 30, background: '#ffd447',
        width: `${100 * Math.min(1, Math.max(0, (item.end / data.duration)))}%`}}/>
    </div>
  </AbsoluteFill>;
};

const Captions = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sec = frame / fps;
  const segment = data.captions.find(c => sec >= c.start && sec <= c.end + .12);
  if (!segment) return null;
  const total = segment.words.reduce((sum, w) => sum + w.text.length, 0);
  const size = total > 15 ? 72 : 93;
  return <div style={{position: 'absolute', top: 1370, left: '10%', width: '80%',
    minHeight: 240, display: 'flex', justifyContent: 'center', alignItems: 'center',
    flexWrap: 'wrap', alignContent: 'center', gap: 15, overflowWrap: 'anywhere',
    textAlign: 'center', zIndex: 20}}>
    {segment.words.map((w, i) => {
      const active = sec >= w.start && sec <= w.end + .05;
      const pop = spring({frame: Math.max(0, frame - Math.round(w.start * fps)), fps,
        config: {damping: 11, mass: .8, stiffness: 260}});
      return <span key={`${w.start}-${i}`} style={{fontFamily: 'Anton, Impact, sans-serif',
        color: active ? '#ffdf26' : 'white', fontSize: size, lineHeight: 1.09,
        WebkitTextStroke: '9px #0b0b0c', paintOrder: 'stroke fill',
        textShadow: '0 8px 0 #000c, 0 12px 20px #000b', textTransform: 'uppercase',
        transform: `scale(${active ? .91 + .13 * pop : 1})`,
        display: 'inline-block', maxWidth: '100%', overflowWrap: 'anywhere'}}>{w.text}</span>;
    })}
  </div>;
};

const Video = () => <AbsoluteFill style={{background: '#05151f'}}>
  {data.beats.map(beat => <Sequence key={beat.beat}
    from={Math.round(beat.start * FPS)}
    durationInFrames={Math.max(1, Math.round(beat.end * FPS) - Math.round(beat.start * FPS))}>
    <Scene item={beat} />
  </Sequence>)}
  <Captions />
</AbsoluteFill>;

const FPS = 30;
const Root = () => <Composition id="Short" component={Video}
  durationInFrames={Math.ceil(data.duration * FPS)} fps={FPS} width={1080} height={1920} />;
registerRoot(Root);
