"""Only targeted street/spotlight/cockpit proofs and two one-frame1080 benchmarks."""
import bpy,sys,math,time,json,argparse,runpy
from pathlib import Path
from mathutils import Vector,Quaternion
from bpy_extras.object_utils import world_to_camera_view
P=Path('/workspace/stray');PROD=P/'production';OUT=P/'previews/repairs_v6';OUT.mkdir(exist_ok=True)
argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ap=argparse.ArgumentParser();ap.add_argument('--stage',default='street');a=ap.parse_args(argv)
code=(PROD/'staging_v5.py').read_text();code=code[:code.index('# Segment rendering only.')]
sys.argv=['staging_v5.py','--','--stage','library'];N={'__name__':'stray_v5_library','__file__':str(PROD/'staging_v5.py')};exec(compile(code,str(PROD/'staging_v5.py'),'exec'),N)
G=N['G'];previous=N['update'];s=N['s'];hero=N['hero'];cam=N['cam'];camd=N['camd'];carpos=N['carpos'];smooth=N['smooth'];visible=N['visible'];box=N['box'];rod=N['rod'];empty=N['empty'];M=N['M'];interp=N['interp'];wt=G['worldtime']
# Integrate delivered fleet collections only, no Preview, no source edits or remodelling.
oldpolice=G['police'];oldheli=G['heli'];oldtruck=G['truck']
with bpy.data.libraries.load(str(PROD/'fleet_snapshot_v6.blend'),link=False) as (src,dst):dst.collections=['Police','Heli','Truck']
for c in dst.collections:
 s.collection.children.link(c);c.hide_render=False;c.hide_viewport=False
 for o in c.all_objects:o.hide_render=False;o.hide_viewport=False
police0=bpy.data.objects['Police_Root'];heli=bpy.data.objects['Heli_Root'];truck=bpy.data.objects['Truck_Root']
def clone_tree(root,suffix):
 mapping={}
 for o in [root,*root.children_recursive]:
  c=o.copy();c.name=o.name+suffix;s.collection.objects.link(c);mapping[o]=c
 for o,c in mapping.items():c.parent=mapping.get(o.parent,o.parent)
 return mapping[root]
police=[police0,clone_tree(police0,'_CHASE1'),clone_tree(police0,'_CHASE2')]
# Remove ONLY shot-owned proxy trees, after all references are remapped.
G['police']=police;N['police']=police;G['heli']=heli;N['heli']=heli;G['truck']=truck;N['truck']=truck
G['rotor']=bpy.data.objects['Heli_MainRotor'];G['beam']=empty('V6 unused former proxy beam')
for root in [*oldpolice,oldheli,oldtruck]:
 for o in [*root.children_recursive,root]:
  if o.name in bpy.data.objects:bpy.data.objects.remove(o,do_unlink=True)
mainrotor=bpy.data.objects['Heli_MainRotor'];tailrotor=bpy.data.objects['Heli_TailRotor']
# Reuse exact night-paint values already approved from render_hero_night.py, not its scene main().
paint=bpy.data.materials.get('Hero_Mat_paint');glass=bpy.data.materials.get('Hero_Mat_glass')
def surface(m,color,rough,metal,spec):
 m.diffuse_color=(*color,1);p=m.node_tree.nodes.get('Principled BSDF')
 for k,v in {'Base Color':(*color,1),'Roughness':rough,'Metallic':metal,'Specular IOR Level':spec,'Coat Weight':0}.items():p.inputs[k].default_value=v
surface(paint,(.008,.009,.011),.34,.05,.19);surface(glass,(.003,.005,.008),.23,0,.16)
# Coordinator approved reusable helpers at23:35 Asia/Shanghai. No demo main()/Preview rigs imported.
materials=runpy.run_path(str(P/'assets/codex/hero_night_materials.py'))['apply_hero_night_materials'](glass='dark',root=hero)
paint=materials['paint'];glass=materials['glass']
if a.stage in ['cockpit','all','next']:
 old_interior=N['interior']
 N['hud']=empty('V6 retired temporary HUD sentinel')
 for o in [*old_interior.children_recursive,old_interior]:
  if o.name in bpy.data.objects:bpy.data.objects.remove(o,do_unlink=True)
 runpy.run_path(str(P/'assets/codex/build_cockpit.py'))['build_cockpit'](root=hero)
 materials=runpy.run_path(str(P/'assets/codex/hero_night_materials.py'))['apply_hero_night_materials'](glass='clear',root=hero)
 glass=materials['glass']
 for o in hero.children_recursive:
  if o.type=='FONT' and any(x in o.data.body for x in ['STRAY','NIGHT DRIVE']):o.data.body=''
 anchor=bpy.data.objects['Hero_MapAnchor']
 nav=[(-.13,-.1,.21),(-.03,-.1,.21),(-.03,.08,.21),(.09,.08,.21),(.09,.27,.21)]
 for p0,p1 in zip(nav,nav[1:]):rod('V6 actual cockpit navigation',p0,p1,.004,'cyan',anchor)
 rod('V6 map destination',(.04,.22,.21),(.09,.27,.21),.005,'yellow',anchor)

# One continuous road650..800: ONLY650..710 curls, and only after Hero has fully cleared it.
box('V6 retained road ahead',(0,755,-.18),(25,90,.35),'road')
box('V6 service deck below roll',(0,680,-4.35),(26,65,.5),'building')
slabs=G['curl'];L=60/22
for i,o in enumerate(slabs):
 o.scale.y=L/6.98
 # Markings already present as children; no added art pass.

def fold_pose(i,t):
 phase=smooth((t-36.8)/2);theta=i/21*math.pi*1.15;start=Vector((0,710-(i+.5)*L,-.18));final=Vector((0,710-16.6*math.sin(theta),16.6*(1-math.cos(theta))-.18));return start.lerp(final,phase),-theta*phase

def cop_release():
 pos,ang=fold_pose(8,37.5);return pos+Vector((2,-.2*math.sin(ang),.2*math.cos(ang))),ang
release,release_angle=cop_release();explosion_origin=release+Vector((0,-3*1.7,4*1.7-4.905*1.7**2))
# Spotlight lens/emitter physically on aircraft underside; actual light used by Eevee.
spot=N['spot'];ld=N['ld'];ld.energy=16000;ld.spot_size=math.radians(45);ld.spot_blend=.7;ld.shadow_soft_size=.1
lens=N['ico']('V6 helicopter searchlight lens',(0,1.7,1.0),(.2,.2,.12),'white',heli)

# Strict body-local windshield path. Same path used in reverse on exit.
def cockpit_pose(t):
 entry=smooth((t-31)/1.4);exit=smooth((t-34.2)/1.4)
 local=Vector((-.327,1.65,.966)).lerp(Vector((-.327,-.53,.966)),entry)
 if t>=34.2:local=Vector((-.327,-.53,.966)).lerp(Vector((-.327,1.65,.966)),exit)
 # Entry looks through front windshield into cabin, then pans in place toward dashboard.
 inward=Vector((-.29,-.82,.86))-local;forward=Vector((.037,1.21,-.09))
 qi=inward.to_track_quat('-Z','Y');qf=forward.to_track_quat('-Z','Y')
 turn=smooth((t-32.4)/.7);q=qi.slerp(qf,turn)
 return local,q

def aim(pos,target,lens):
 cam.location=pos;cam.rotation_mode='QUATERNION';cam.rotation_quaternion=(Vector(target)-cam.location).to_track_quat('-Z','Y');camd.lens=lens

def update(t,scene='street'):
 previous(t);p=carpos(t)
 # New aircraft has root at skid ground, so use its actual asset height.
 if t<39:heli.location=(p.x+4,p.y+14,8.5)
 mainrotor.rotation_euler.z=wt(t)*26;tailrotor.rotation_euler.x=wt(t)*45
 for root in police+[truck]:
  for o in root.children:
   if '_Wheel_' in o.name:o.rotation_euler.x=-root.location.y/.35
 # Independent lightbar emitters; shared materials keep coherent world-time slowdowns.
 for color,phase in [('red',0),('blue',.5)]:
  m=bpy.data.materials.get('Police_Mat_'+color)
  if m:m.node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=7 if (wt(t)*5+phase)%1<.45 else .2
 # Street remains flat for .8s of excerpt, then curls BEHIND Hero, never into it or camera.
 for i,o in enumerate(slabs):
  pos,ang=fold_pose(i,t);o.location=pos;o.rotation_euler=(ang,0,0);o.scale.y=L/6.98
 if 35<t<36.8:
  q=carpos(t-2);q.x=2;q.z=0;police[1].location=q;police[1].rotation_euler=(0,0,0)
 if 36.4<t<=36.8:
  q=police[1].location.copy();target,_=fold_pose(8,36.8);target+=Vector((2,0,.2));police[1].location=q.lerp(target,smooth((t-36.4)/.4))
 if 36.8<t<=37.5:
  pos,ang=fold_pose(8,t);police[1].location=pos+Vector((2,-.2*math.sin(ang),.2*math.cos(ang)));police[1].rotation_euler=(ang,0,0)
 if t>37.5:
  d=t-37.5;police[1].location=release+Vector((0,-3*d,4*d-4.905*d*d));police[1].rotation_euler=(release_angle+d,d*.5,.1)
 dt=t-39.2
 for o,v,sz in G['fx'][1][2]:
  visible(o,0<dt<3)
  if dt>0:o.location=explosion_origin+v*dt*4;o.scale=(max(.01,math.sin(min(1,dt/2)*math.pi)*sz*3.5),)*3
 # Real spotlight points at an actual patch of road, with distance falloff and geometric occlusion.
 spot.location=heli.matrix_world@Vector((0,1.7,1));target=Vector((p.x,p.y+8,.06));spot.rotation_euler=(target-spot.location).to_track_quat('-Z','Y').to_euler();ld.energy=16000 if 24<t<29 else 0
 if scene=='street':
  aim(p+Vector((-7,28,12)),p+Vector((0,-8,7)),21)
 elif scene=='spotlight':
  aim(p+Vector((-9,-20,8)),p+Vector((1,7,4.5)),23)
 elif scene=='cockpit':
  # Matrix multiply, not world-space addition: camera shares root velocity/attitude exactly.
  bpy.context.view_layer.update();local,q=cockpit_pose(t);cam.location=hero.matrix_world@local;cam.rotation_mode='QUATERNION';cam.rotation_quaternion=hero.matrix_world.to_quaternion()@q;camd.lens=20
 return p

# Capture actual full scene diagnostics before choosing benchmark configurations.
def diagnostic():
 return {'blender':bpy.app.version_string,'engine':s.render.engine,'objects':len(s.objects),'meshes':sum(o.type=='MESH' for o in s.objects),'lights':[{ 'name':o.name,'type':o.data.type,'shadow':o.data.use_shadow,'energy':o.data.energy} for o in s.objects if o.type=='LIGHT'],'raytracing':s.eevee.use_raytracing,'taa_render_samples':s.eevee.taa_render_samples,'resolution':[s.render.resolution_x,s.render.resolution_y],'threads':s.render.threads}
s.render.threads_mode='FIXED';s.render.threads=3;s.render.fps=60;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';s.render.dither_intensity=0

def workbench():
 s.render.engine='BLENDER_WORKBENCH';s.render.use_compositing=False;sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_shadows=True;sh.show_object_outline=True;sh.object_outline_color=(.003,.003,.012);sh.show_backface_culling=True;sh.background_type='WORLD';s.world.color=(.012,.016,.045);s.display.render_aa='FXAA';s.view_settings.exposure=.7

def eevee(samples=4):
 s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=samples;s.eevee.use_raytracing=False;s.render.use_compositing=True;s.view_settings.exposure=0

def render_clip(name,start,end,fps,scene,engine):
 folder=OUT/name;folder.mkdir(exist_ok=True);frames=round((end-start)*fps);qa=[];st=time.perf_counter()
 for i in range(frames):
  t=start+i/fps;p=update(t,scene);bpy.context.view_layer.update();center=hero.matrix_world@Vector((0,0,.65));ndc=world_to_camera_view(s,cam,center);direction=center-cam.location;hit,loc,no,fi,obj,ma=s.ray_cast(bpy.context.evaluated_depsgraph_get(),cam.location,direction.normalized(),distance=direction.length)
  camlocal=hero.matrix_world.inverted()@cam.location
  row={'time':t,'hero_center':[round(v,4) for v in ndc],'center_in_frame':0<ndc.x<1 and 0<ndc.y<1 and ndc.z>0,'first_object':obj.name if hit else None,'camera_root_local':[round(v,5) for v in camlocal],'hero_y':round(p.y,3),'max_fold_y':round(max(o.location.y+L/2 for o in slabs),3)};qa.append(row)
  s.render.filepath=str(folder/f'{i:04d}.png');bpy.ops.render.render(write_still=True);(PROD/'v6_progress.json').write_text(json.dumps({'pid':__import__('os').getpid(),'clip':name,'frame':i+1,'total':frames,'time':t}))
 (folder/'qa.json').write_text(json.dumps(qa,indent=2));r={'name':name,'start':start,'end':end,'fps':fps,'frames':frames,'engine':engine,'resolution':[s.render.resolution_x,s.render.resolution_y],'render_seconds':round(time.perf_counter()-st,2),'folder':str(folder)};print('V6_CLIP_DONE',json.dumps(r),flush=True);return r

reports=[]
if a.stage in ['street','all','next']:
 workbench();s.render.resolution_x=640;s.render.resolution_y=360;s.render.resolution_percentage=100;reports.append(render_clip('street_curl',36,40,12,'street','BLENDER_WORKBENCH'))
if a.stage in ['spotlight','all']:
 eevee(4);s.render.resolution_x=480;s.render.resolution_y=270;s.render.resolution_percentage=100;reports.append(render_clip('spotlight',24.2,28.2,8,'spotlight','BLENDER_EEVEE_NEXT'))
if a.stage in ['cockpit','all','next']:
 # Clean blended tinted pane; geometry retained, no hide/toggle during transit.
 p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.07,.13,.18,1);p.inputs['Alpha'].default_value=.10;p.inputs['Roughness'].default_value=.06;p.inputs['Metallic'].default_value=0;p.inputs['Transmission Weight'].default_value=0;glass.diffuse_color=(.07,.13,.18,.10);glass.surface_render_method='BLENDED';glass.use_backface_culling=False
 eevee(4);s.render.resolution_x=480;s.render.resolution_y=270;s.render.resolution_percentage=100
 reports.append(render_clip('cockpit_entry',31,33,12,'cockpit','BLENDER_EEVEE_NEXT'));reports.append(render_clip('cockpit_exit',34,36,12,'cockpit','BLENDER_EEVEE_NEXT'))
if reports:(PROD/('v6_'+a.stage+'.json')).write_text(json.dumps(reports,indent=2))
if a.stage in ['bench','next']:
 # Same scene, camera, dimensions and1080 resolution for BOTH rendered images; no story geometry removed.
 previous(22.4);s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100;eevee(32);diagn=diagnostic();(PROD/'benchmark_v6_diagnostics.json').write_text(json.dumps(diagn,indent=2));bench=[]
 for name,samples,fast in [('quality32',32,False),('fast4',4,True)]:
  eevee(samples)
  if fast:
   for o in s.objects:
    if o.type=='LIGHT':o.data.use_shadow=False
   area=[o for o in s.objects if o.type=='LIGHT' and o.data.type=='AREA']
   if len(area)>2:area[1].data.energy=0
   s.render.use_compositing=False
  s.render.filepath=str(OUT/f'benchmark1080_{name}.png');st=time.perf_counter();bpy.ops.render.render(write_still=True);secs=time.perf_counter()-st;bench.append({'name':name,'samples':samples,'seconds':round(secs,4),'resolution':[1920,1080],'path':s.render.filepath,'shadows':not fast,'compositor_glow':not fast,'story_geometry_removed':False});(PROD/'benchmark_v6.json').write_text(json.dumps(bench,indent=2));print('V6_BENCH',json.dumps(bench[-1]),flush=True)
