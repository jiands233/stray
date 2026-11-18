from pathlib import Path
import json,subprocess
P=Path('/workspace/stray');PROD=P/'production';OUT=P/'previews/repairs_v5'
rows=[]
for name in ['geometry','spotlight']:
 f=PROD/('repairs_'+name+'.json')
 if f.exists():rows+=json.loads(f.read_text())
result=[]
for r in rows:
 dest=OUT/(r['name']+'.mp4');dur=r['end']-r['start'];cmd=['ffmpeg','-v','error','-y','-framerate',str(r['fps']),'-i',r['folder']+'/%04d.png','-ss',str(r['start']),'-i',str(P/'audio/preview_mix.wav'),'-t',str(dur)]
 if r['end']==60:cmd+=['-vf','fade=t=out:st=%s:d=2'%max(0,58-r['start'])]
 cmd+=['-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',str(dest)]
 subprocess.run(cmd,check=True)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=width,height,r_frame_rate,nb_frames:format=duration,size','-of','json',str(dest)]));result.append({'file':str(dest),'story_start':r['start'],'story_end':r['end'],'probe':probe})
(PROD/'repair_videos.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
