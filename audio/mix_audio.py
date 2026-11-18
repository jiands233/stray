from pathlib import Path
import numpy as np, subprocess, wave, json
P=Path('/workspace/stray/audio');R=48000;D=60;n=R*D;t=np.arange(n)/R

def decode(path):
 b=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-acodec','pcm_f32le','-ar',str(R),'-ac','2','-']);return np.frombuffer(b,dtype='<f4').reshape(-1,2)
def smooth(v):v=np.clip(v,0,1);return v*v*(3-2*v)
def wt(t):
 r=np.asarray(t,dtype=float).copy()
 for lo,hi,speed in [(6.8,8.8,.18),(47.3,49,.3),(53,54.5,.35)]:r-=(1-speed)*np.clip(t-lo,0,hi-lo)
 return r
world=wt(t);fx=np.zeros((n,2),np.float32)
def sample(x,pos):
 pos=np.clip(pos,0,len(x)-1.01);i=pos.astype(np.int64);f=(pos-i).astype(np.float32)[:,None];return x[i]*(1-f)+x[i+1]*f
def loop(x,clock):
 # 80ms equal-power crossfade at wrap, all content remains recorded sound.
 span=len(x)-int(.08*R);pos=(clock*R)%span;v=sample(x,pos);k=pos<int(.08*R)
 if k.any():
  u=(pos[k]/(.08*R)).astype(np.float32)[:,None];v[k]=v[k]*u+sample(x,pos[k]+span)*(1-u)
 return v
eng=decode(P/'engine.mp3');sir=decode(P/'siren.mp3');hel=decode(P/'helicopter.mp3');blast=decode(P/'explosion.mp3');glass=decode(P/'glass_recorded.mp3')
engine_env=.2+.1*np.exp(-((t-1.2)/.28)**2)+.16*np.exp(-((t-2.7)/.3)**2)+.1*smooth((t-4)/2)
fx+=loop(eng,world)*engine_env[:,None]
sirenv=smooth((t-1.4)/1.2)*(1-smooth((t-48)/2))*.23
fx+=loop(sir,world)*sirenv[:,None]
helenv=smooth((t-23.8)/1.5)*(1-smooth((t-39)/2))*.4
fx+=loop(hel,np.maximum(0,world-wt(np.array([24.]))[0]))*helenv[:,None]
def event(x,at,gain=1,rate=1):
 mask=t>=at;pos=(world[mask]-wt(np.array([at]))[0])*R*rate;valid=(pos>=0)&(pos<len(x)-1);idx=np.where(mask)[0][valid];fx[idx]+=sample(x,pos[valid])*gain
for at,gain in [(10.285714,.35),(22.5,1),(30,.55),(39.2,.9)]:event(blast,at,gain,.65 if at in [22.5,39.2] else 1)
event(glass,30,.4);event(glass,49.2,.9)
# One uninterrupted original music interval; no stitched bars, retime, or fabricated silence.
start=44.573286;music=decode(P/'punch-deck-alive.mp3');offset=round(start*R);m=music[offset:offset+n].copy()
if len(m)!=n:raise RuntimeError('Original track too short')
m*=.62
fade=(1-smooth((t-58)/2)).astype(np.float32)[:,None]
for name,x in [('sfx_only',fx),('music_contiguous',m),('preview_mix',fx+m)]:
 x=x*fade;peak=float(np.max(np.abs(x)));scale=min(1,.97/max(.001,peak));out=(x*scale*32767).astype('<i2')
 with wave.open(str(P/(name+'.wav')),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(R);w.writeframes(out.tobytes())
 print(name,peak,scale)
(P/'mix_manifest.json').write_text(json.dumps({'duration':60,'sample_rate':R,'music_title':'Alive','music_author':'Punch Deck','publisher_bpm':105,'bpm_independently_measured':False,'music_original_start_seconds':start,'music_original_end_seconds':start+60,'drop_source_seconds':54.859,'drop_picture_seconds':10.285714,'music_retimed':False,'music_mid_cuts':False,'music_silence_before_drop':'Not verified; no artificial silence inserted','diegetic_audio_time_mapping':'same world-time slowdowns as scene, recordings resampled not synthesized','audition_status':'NOT auditioned; waveform-based rough mix for supervisor review'},indent=2))
