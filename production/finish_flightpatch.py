from pathlib import Path
import json,shutil,subprocess
P=Path('/workspace/stray');base=P/'previews/repairs_v5';src=base/'custom_56.0_60.0'
files=sorted(src.glob('*.png'))
if len(files)!=48:raise RuntimeError(f'Flight patch incomplete: {len(files)}/48')
qa=json.loads((src/'camera_qa.json').read_text())
bad=[r for r in qa if not r['center_inside_frame']]
if bad:raise RuntimeError(f'Flight patch still has {len(bad)} off-frame hero centers')
for i,f in enumerate(files):shutil.copy2(f,base/'flight_tunnel'/f'{i:04d}.png')
(base/'flight_tunnel/camera_qa.json').write_text(json.dumps(qa,indent=2))
for i,f in enumerate(files[:24]):shutil.copy2(f,base/'fall_ignition'/f'{36+i:04d}.png')
old=json.loads((base/'fall_ignition/camera_qa.json').read_text());old=old[:36]+qa[:24];(base/'fall_ignition/camera_qa.json').write_text(json.dumps(old,indent=2))
(P/'production/flight_patch_applied.json').write_text(json.dumps({'patch_folder':str(src),'actual_unique_frames_rendered':48,'shared_overlap_frames_copied':24,'interpolation':False,'flight_hero_center_outside_frames':len(bad)},indent=2))
subprocess.run(['python3',str(P/'production/encode_repairs.py')],check=True)
subprocess.run(['python3',str(P/'production/review_repairs.py')],check=True)
