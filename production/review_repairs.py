from pathlib import Path
from PIL import Image,ImageDraw
import json
P=Path('/workspace/stray/previews/repairs_v5');summary=[]
for folder in sorted(P.iterdir()):
 if not folder.is_dir() or folder.name.startswith('still_'):continue
 files=sorted(folder.glob('*.png'))
 if not files:continue
 inds=sorted(set([0,len(files)//4,len(files)//2,len(files)*3//4,len(files)-1]))
 out=Image.new('RGB',(640,205*len(inds)),'#12142a');d=ImageDraw.Draw(out)
 for n,k in enumerate(inds):
  out.paste(Image.open(files[k]).resize((640,360)).resize((320,180)),(0,n*205));d.text((325,n*205+12),f'{folder.name}\nframe {k}/{len(files)-1}',fill='white')
 out.save(P/(folder.name+'_contact.jpg'))
 qa=folder/'camera_qa.json'
 if qa.exists():
  q=json.loads(qa.read_text());bad=[r for r in q if not r['center_inside_frame']];block=[r for r in q if r['first_object_on_camera_to_hero'] and not r['first_object_on_camera_to_hero'].startswith(('Hero_','V5 '))];summary.append({'segment':folder.name,'frames':len(q),'hero_center_outside_frames':bad,'nonhero_occlusion_frames':block})
Path('/workspace/stray/production/repairs_camera_summary.json').write_text(json.dumps(summary,indent=2))
print([(s['segment'],s['frames'],len(s['hero_center_outside_frames']),len(s['nonhero_occlusion_frames'])) for s in summary])
