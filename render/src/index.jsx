import React from 'react';
import {registerRoot, Composition, AbsoluteFill, OffthreadVideo, Img,
        Sequence, staticFile, useCurrentFrame, useVideoConfig,
        interpolate, spring} from 'remotion';
import '@fontsource/anton/400.css';
import data from '../public/data.json';
import {captionWidthPx} from './motion.js';

const FPS = 30;

// Only video B-roll rendered to portrait by FFmpeg. Never insert static cards.
const Broll = ({shot}) => {
  if (!shot.asset?.file || shot.asset?.type !== 'video') {
    throw new Error('Empty visual beat ' + shot.beat);
  }
  return <AbsoluteFill>
    <OffthreadVideo src={staticFile('media/' + shot.asset.file)}
      muted pauseWhenBuffering={false}
      style={{position:'absolute', width:1080, height:1920,
              objectFit:'cover', inset:0}}/>
  </AbsoluteFill>;
};
const important = word =>
  String(word).length >= 4 && !['LA','EL','LOS','LAS','DE','DEL','UNA',
    'UN','EN','Y','O','A','QUE','SUS','SU','POR']
    .includes(String(word).toLocaleUpperCase('es'));

const Captions = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame/fps;
  const cue = data.captions.find(c => t >= c.start && t < c.end);
  if (!cue || cue.words?.length !== 1) return null;
  const word = cue.words[0].text.toLocaleUpperCase('es');
  const at = Math.max(0, frame-Math.round(cue.start*fps));
  const pop = spring({frame:at,fps,config:{damping:12,stiffness:280}});
  const scale = .84 + .16*pop;
  const hook = t < 3 && important(word);
  const textColor = hook ? '#ff3131' : '#ffffff';
  const glow = hook ? '0 0 17px #ff9a2e, 0 0 38px #e52321' : '0 6px 14px #000b';
  return <div style={{position:'absolute',inset:0,display:'flex',
    alignItems:'center',justifyContent:'center',zIndex:20,pointerEvents:'none'}}>
    <svg viewBox="0 0 972 210" width="90%" height="210"
      preserveAspectRatio="xMidYMid meet" style={{overflow:'visible'}}>
      <text x="486" y="105" dominantBaseline="middle" textAnchor="middle"
        textLength={captionWidthPx(word)} lengthAdjust="spacingAndGlyphs"
        fontFamily="Anton, Impact, sans-serif" fontSize="112"
        fill={textColor} stroke="#090909" strokeWidth="8"
        strokeLinejoin="round" paintOrder="stroke fill"
        style={{textShadow:glow,transform:'scale('+scale+')',
          transformOrigin:'486px 105px'}}>
        {word}
      </text>
    </svg>
  </div>;
};

// One transient glow/explosion transition at the end of the opening hook.
const HookImpact = () => {
  const frame=useCurrentFrame();
  const t=frame/FPS;
  if(t<2.94 || t>3.25) return null;
  const p=Math.min(1,Math.max(0,(t-2.94)/.31));
  return <AbsoluteFill style={{
    pointerEvents:'none',zIndex:15,opacity:Math.sin(Math.PI*p)*.52,
    background:'radial-gradient(circle at 50% 50%, #ffe4a0 0%, #fa3a19 28%, transparent 75%)',
    transform:'scale('+(.85+1.4*p)+')'}}/>;
};
const Mascot = ({event}) => {
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const len=Math.max(1,Math.round((event.end-event.start)*fps));
  const entrance=spring({frame,fps,config:{mass:.65,damping:15,stiffness:180}});
  const exit=interpolate(frame,[Math.max(0,len-10),len],[1,0],
                         {extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const lift=(1-entrance)*320+(1-exit)*240;
  return <div style={{position:'absolute',bottom:10,left:'50%',
    width:440,height:520,pointerEvents:'none',zIndex:18,
    transform:'translateX(-50%) translateY('+lift+'px)',
    opacity:Math.max(0,Math.min(1,entrance*exit))}}>
    <Img src={staticFile('media/'+event.file)}
      style={{width:'100%',height:'100%',objectFit:'contain'}}/>
  </div>;
};
const Video = () => <AbsoluteFill>
  {data.beats.map(beat =>
    <Sequence key={beat.beat} from={Math.round(beat.start*FPS)}
      durationInFrames={Math.max(1,Math.round(beat.end*FPS)-Math.round(beat.start*FPS))}>
      <Broll shot={beat}/>
    </Sequence>)}
  <HookImpact/>
  {data.mascots?.map((event,i) =>
    <Sequence key={i} from={Math.round(event.start*FPS)}
      durationInFrames={Math.max(1,Math.round(event.end*FPS)-Math.round(event.start*FPS))}>
      <Mascot event={event}/>
    </Sequence>)}
  <Captions/>
</AbsoluteFill>;
const Root = () => <Composition id="Short" component={Video}
  durationInFrames={Math.ceil(data.duration*FPS)} fps={FPS}
  width={1080} height={1920}/>;
registerRoot(Root);
