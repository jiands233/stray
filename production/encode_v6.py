from pathlib import Path
import json,subprocess
P=Path('/workspace/stray');PROD=P/'production';OUT=P/'previews/repairs_v6';rows={}
for name in ['v6_clips.log','v6_next.log']:
 f=PROD/name
 if not f.exists():continue
 for line in f.read_text(errors='replace').splitlines():
  if line.startswith('V6_CLIP_DONE '):
   r=json.loads(line[len('V6_CLIP_DONE '):]);rows[r['name']]=r
progress_file=PROD/'v6_progress.json'
progress=json.loads(progress_file.read_text()) if progress_file.exists() else {}
results=[]
for name,r in rows.items():
 if progress.get('clip')==name and progress.get('frame',0)<progress.get('total',0):continue
 folder=Path(r['folder'])
 if len(list(folder.glob('*.png')))!=r['frames']:continue
 out=OUT/(name+'.mp4');tmp=OUT/(name+'.encoding.mp4')
 subprocess.run(['ffmpeg','-v','error','-y','-framerate',str(r['fps']),'-i',str(folder/'%04d.png'),'-ss',str(r['start']),'-i',str(P/'audio/preview_mix.wav'),'-t',str(r['end']-r['start']),'-c:v','libx264','-threads','2','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(tmp)],check=True);tmp.replace(out)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=width,height,r_frame_rate,nb_frames','-of','json',str(out)]));results.append({'file':str(out),**r,'probe':probe})
(PROD/'v6_videos.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
