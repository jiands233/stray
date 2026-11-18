"""Narrative repairs. Low-cost problem-segment proofs only, never final rendering."""
from bpy_extras.object_utils import world_to_camera_view
import bpy,sys,runpy,math,os,time,json,argparse
from pathlib import Path
from mathutils import Vector
ROOT=Path('/workspace/stray');PROD=ROOT/'production';OUT=ROOT/'previews/repairs_v5';OUT.mkdir(exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ap=argparse.ArgumentParser();ap.add_argument('--stage',default='geometry');ap.add_argument('--start',type=float,default=-1);ap.add_argument('--end',type=float,default=-1);a=ap.parse_args(args)
sys.argv=['build_scene.py','--','--mode','build','--asset-mode','codex','--asset-file',str(PROD/'hero_asset_snapshot.blend')]
ret=runpy.run_path(str(PROD/'build_scene.py'));G=ret['update'].__globals__;old=G['update'];s=G['s'];cam=G['cam'];camd=G['camd'];hero=G['hero'];police=G['police'];heli=G['heli'];truck=G['truck'];M=G['M'];box=G['box'];rod=G['rod'];ico=G['ico'];mesh=G['mesh'];visible=G['visible'];smooth=G['smooth'];interp=G['interp'];carpos=G['carpos'];empty=G['empty']
G['batch']={}
# All camera/road repairs happen in existing world; no shot changes or hidden relocation.
# Actual cliff mass, exposed cut face, lower canyon floor and foundations.
box('V5 cliff mass',(0,1070,-23),(28,140,45.5),'building',batchit=True)
box('V5 cut rock face',(0,1140,-22.7),(28,.3,45),'silver',batchit=True)
box('V5 canyon floor',(0,1320,-43),(160,370,2),'road',batchit=True)
for x in [-13.5,13.5]:
 rod('V5 edge rail',(x,1080,.65),(x,1138,.65),.1,'yellow')
for i in range(10):box('V5 cliff warning',(-12+i*2.6,1136,.05),(1.4,1.4,.035),'yellow',batchit=True)
for z in [-7,-15,-23,-31,-39]:box('V5 exposed foundation seam',(0,1140.18,z),(28,.1,.28),'ink',batchit=True)
for x in [-11,11]:rod('V5 exposed utility pipe',(x,1140.3,-42),(x,1140.3,0),.12,'cyan')
# Dense real canyon geometry reaches below camera/hero, not floating at street level.
for side in [-1,1]:
 for j,y in enumerate(range(1165,1480,24)):
  x=side*(23+(j%2)*2);h=92+(j%3)*12
  box('V5 canyon tower',(x,y,-42+h/2),(14,21,h),'building' if j%2 else 'building2',batchit=True)
  for zz in range(-30,46,10):
   for yy in [-5,0,5]:box('V5 canyon windows',(side*15.95,y+yy,zz),(.08,2.4,2),'cyan' if (j+yy)%2 else 'pink',batchit=True)
  rod('V5 canyon rim',(side*15.9,y-10,-35),(side*15.9,y-10,48),.075,'violet')
for y in [1240,1310,1380]:
 box('V5 skybridge',(0,y,51),(46,10,5),'building2',batchit=True)
 box('V5 skybridge light',(0,y-5.1,49),(28,.1,.15),'cyan',batchit=True)
for material,(vertices,faces) in G['batch'].items():mesh('V5 static '+material,vertices,faces,material)
G['batch']={}
# Procedural interior purposefully simple, physically inside the real asset cabin.
interior=empty('V5 cockpit interior');interior.parent=hero
for x in [-.29,.29]:
 box('V5 seat cushion',(x,-.45,.48),(.44,.5,.13),'ink',interior,.03)
 o=box('V5 seat back',(x,-.74,.72),(.43,.13,.5),'silver',interior,.04);o.rotation_euler.x=-.18
box('V5 dashboard',(0,.58,.765),(1.17,.24,.16),'ink',interior,.035)
box('V5 instrument fascia',(0,.45,.82),(1.12,.025,.16),'silver',interior,.015)
box('V5 console',(0,-.03,.53),(.13,.85,.2),'ink',interior,.02)
for x in [-.55,.55]:
 rod('V5 cabin sill',(x,-.65,.76),(x,.65,.76),.023,'cyan',interior)
 rod('V5 A pillar',(x,.2,1.13),(x,.82,.76),.024,'ink',interior)
# Steering wheel, hub and spokes, faces driver at -Y.
bpy.ops.mesh.primitive_torus_add(major_radius=.155,minor_radius=.022,major_segments=32,minor_segments=8,location=(-.29,.26,.87),rotation=(math.pi/2,0,0));wheel=bpy.context.object;wheel.name='V5 steering wheel';wheel.parent=interior;wheel.data.materials.append(M['silver'])
for ang in [0,2.1,4.2]:rod('V5 steering spoke',(-.29,.26,.87),(-.29+.14*math.cos(ang),.26,.87+.14*math.sin(ang)),.012,'ink',interior)
box('V5 steering hub',(-.29,.25,.87),(.1,.045,.08),'ink',interior,.018)
# Actual instrument panel: gauge arc/rpm bars, no labels/subtitles.
for x in [-.41,-.17]:
 for i in range(16):
  theta=.25+i/15*2.6
  p=(x+.085*math.cos(theta),.426,.855+.06*math.sin(theta));q=(x+.085*math.cos(theta+.08),.426,.855+.06*math.sin(theta+.08));rod('V5 luminous gauge',p,q,.004,'cyan',interior)
# GPS is an irregular road route on a physical display, not a fence/grid.
gps=box('V5 GPS screen',(.25,.428,.86),(.39,.018,.19),'ink',interior,.012)
for route,col in [([(-.15,-.06),(-.07,-.06),(-.07,.02),(.04,.02),(.04,.065),(.15,.065)],'yellow'),([(-.16,.03),(-.1,.03),(-.02,-.04),(.12,-.04),(.15,-.07)],'cyan')]:
 for (x,z),(xx,zz) in zip(route,route[1:]):rod('V5 GPS road',(.25+x,.414,.86+z),(.25+xx,.414,.86+zz),.0035,col,interior)
# HUD route projected just over physical dashboard; roads are non-grid and arrow-led.
hud=empty('V5 HUD');hud.parent=interior
for coords,col in [([(-.11,.74,.94),(.05,.74,.94),(.05,.78,1.02),(.25,.78,1.02),(.35,.82,1.1)],'cyan'),([(.02,.74,.94),(.05,.78,1.02),(.25,.78,1.02)],'yellow')]:
 for p,q in zip(coords,coords[1:]):rod('V5 HUD active route',p,q,.007,col,hud)
mesh('V5 HUD navigation arrow',[(.21,.77,1.015),(.25,.77,1.055),(.29,.77,1.015)],[(0,1,2)],'yellow',hud)
# Remove former unframed uniform grid in every render.
visible(G['maproot'],False)
# Actual spotlight, not a gray ellipse standing in for illumination.
visible(G['pool'],False);visible(G['beam'],False)
ld=bpy.data.lights.new('V5 helicopter real searchlight','SPOT');ld.energy=18000;ld.color=(.65,.82,1);ld.spot_size=math.radians(42);ld.spot_blend=.6;ld.use_shadow=True;ld.shadow_soft_size=.2
spot=bpy.data.objects.new(ld.name,ld);s.collection.objects.link(spot)
ico('V5 searchlight lens',(0,.7,-1.1),(.2,.2,.1),'white',heli)
# Ringed/bladed comic blast is true scene mesh geometry with a real collision origin.
starroot=empty('V5 impact star');starroot.location=(0,371,3)
for size,m in [(1.15,'ink'),(1.0,'pink'),(.78,'yellow')]:
 verts=[(0,0,0)]
 for i in range(32):
  ang=2*math.pi*i/32;rr=(1 if i%2==0 else .45)*size;verts.append((math.cos(ang)*rr,0,math.sin(ang)*rr))
 faces=[(0,1+i,1+(i+1)%32) for i in range(32)];o=mesh('V5 comic impact rays',verts,faces,m,starroot);o.location.y=(1.15-size)*-.04
# Debris physically travels from collision, and stays near tanker.
blast_shards=[]
for i in range(20):
 ang=i*2.399;v=Vector((math.cos(ang)*5,math.sin(ang)*4,3+(i%5)));o=ico('V5 collision shard',(0,0,0),(.18,.4,.12),'cyan' if i%3 else 'yellow');blast_shards.append((o,v))
for o in G['curl']:
 box('V5 folding road lane marking',(0,0,.2),(.22,2.7,.02),'yellow',o)
 for x in [-6,6]:box('V5 folding road white lane',(x,0,.2),(.15,2.7,.02),'white',o)
# Global camera anchors, absolute world coordinates so hero/blast cannot outrun framing.
camfix=[(19,(-10,314,7)),(20.3,(-12,337,10)),(21.4,(-12,343,10)),(23.3,(-12,345,10)),(24.6,(-12,396,12)),(26,(-10,458,11)),(28,(-10,520,8))]
# End-state trailing/light-tunnel camera always outside road foundations.
endcam=[(49,(-10,-8,7)),(50.3,(-10,14,9)),(51.5,(-10,30,10)),(52.5,(-10,30,9)),(54.5,(-10,22,7)),(55.5,(-8,8,6)),(57,(-2,-12,4)),(60,(-1,-13,4))]
insidecam=[(30,(-3,11,2)),(31,(-1.5,3,1.3)),(31.8,(-.2,1.45,1.03)),(33,(-.2,-.24,1.01)),(34,(-.2,-.24,1.01)),(35,(-.2,1.45,1.03)),(36,(-7,8,4))]
foldcam=[(35,(-.2,1.45,1.03)),(36,(-10,-30,17)),(37,(-10,-30,17)),(39,(-10,-30,17)),(40,(-10,12,10))]

def aim(pos,target,lens):
 cam.location=pos;cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler();camd.lens=lens

def update(t):
 old(t);p=carpos(t)
 visible(G['maproot'],False);visible(G['pool'],False);visible(G['beam'],False)
 # Interior remains true scene geometry. Only projected HUD activates during takeover.
 visible(hud,32<t<36)
 if t>39:
  heli.location=(p.x+4+70*smooth((t-41)/3),p.y+12,11+120*smooth((t-39)/4))
 # Collision gets an exact ground-level approach. Tanker occupies y370 throughout.
 o=police[0]
 if 20<t<=22.45:
  u=smooth((t-20)/2.45);o.location=Vector((-1,315,0)).lerp(Vector((0,366.2,0)),u);o.rotation_euler=(0,0,0)
 if t>22.45:
  dt=t-22.45;o.location=(0,366.2+min(dt,.3)*2,-min(dt,3)*.3);o.rotation_euler=(min(dt,2)*.6,min(dt,2)*.35,0)
 # Ground-impact cloud appears only after bumper reaches tanker envelope.
 origin,start,cloud=G['fx'][0];dt=t-22.45
 for j,(o,v,sz) in enumerate(cloud):
  visible(o,0<dt<3.1)
  if 0<dt<3.1:
   o.location=Vector((0,370,2))+v*(1+dt*4);r=(1.7+2.6*math.sin(min(1,dt/2.8)*math.pi))*sz;o.scale=(r,r*.8,r)
 visible(starroot,0<dt<.6);starroot.scale=(max(.01,dt*24),)*3
 # Face planar effect towards actual camera; no fake city/vehicle imagery.
 for o,v in blast_shards:
  visible(o,0<dt<2.3);o.location=Vector((0,370,2))+v*max(0,dt)+Vector((0,0,-2*max(0,dt)**2))
 # Curl as one clear assembled arc. First segment rooted near y730; all pieces remain same street.
 phase=smooth((t-35)/2.5)
 for i,o in enumerate(G['curl']):
  theta=i/21*math.pi*1.15;final=Vector((0,730+18*math.sin(theta),18*(1-math.cos(theta))-.18));o.location=Vector((0,650+i*7,-.18)).lerp(final,phase);o.rotation_euler.x=theta*phase;o.scale.y=1-phase+phase*(18*math.pi*1.15/21/6.98)
 # Show the pursuing car falling from the now missing outer lane, not teleporting backward.
 if t>38.1:
  dt2=t-38.1;base=carpos(37.05)+Vector((2,0,0));police[1].location=base+Vector((0,dt2*3,-5*dt2*dt2));police[1].rotation_euler=(dt2,dt2*.3,.2)
 origin2=carpos(37.05)+Vector((2,3.3,-6));dt3=t-39.2
 for o,v,sz in G['fx'][1][2]:
  visible(o,0<dt3<3)
  if dt3>0:o.location=origin2+v*dt3*5;o.scale=(max(.01,math.sin(min(1,dt3/3)*math.pi)*sz*3),)*3
 # Leave final police visible until physically hitting the residual screen edge.
 visible(police[2],True)
 if t>50.7:
  dd=t-50.7;police[2].location=(2,1046+dd*4,-dd*dd*3);police[2].rotation_euler=(dd*.7,dd,.2)
 for o,base in G['screen']:
  hit=49.27 if abs(base.x)<4 else 50.7;dd=max(0,t-hit)
  o.location=base+Vector((base.x*dd*.6,dd*13,dd*4-dd*dd*4));o.rotation_euler=(dd*.6,dd*.7,dd*.3)
 spot.location=heli.location+Vector((0,.7,-1.15));spot.rotation_euler=(Vector((p.x,p.y+8,.05))-spot.location).to_track_quat('-Z','Y').to_euler();ld.energy=18000 if 24<t<33 else 0
 if 19<t<28:
  pos=interp(camfix,t)
  target=Vector((0,372,3)) if t<23.3 else Vector((0,372,3)).lerp(p+Vector((1,7,5)),smooth((t-23.3)/2.7))
  if t>23.7:
   blend=smooth((t-23.7)/1.7);pos=pos.lerp(p+Vector((-10,-18,8)),blend);target=target.lerp(p+Vector((1,6,4)),blend)
  aim(pos,target,25 if t<24 else 24)
 if 30<=t<=36:
  # Cross windshield at y~.6,z~1.0, inside roof envelope (not through roof).
  target=p+Vector((0,8,1))
  if t<31.4:target=(p+Vector((0,0,.8))).lerp(target,smooth((t-30)/1.4))
  aim(p+interp(insidecam,t),target,32-12*smooth((t-30.7)/1.1))
 if 35<t<40:
  target=p+Vector((0,10,10))
  if t<36:target=(p+Vector((0,8,1))).lerp(target,smooth((t-35)/1))
  aim(p+interp(foldcam,t),target,17)
 if t>=49:
  target=p+Vector((0,0,.7))
  if t>56.4:target=target.lerp(p+Vector((0,7,.7)),smooth((t-56.4)/.6))
  aim(p+interp(endcam,t),target,28)
 # Orient impact star to stay at fixed physical world origin, toward camera.
 starroot.rotation_euler=(cam.location-starroot.location).to_track_quat('-Y','Z').to_euler()
 return p

# Segment rendering only. Render each true frame at stated preview FPS.
segments=[('tanker_collision',20,25),('cockpit',31,36),('street_curl',35,40),('ring_context',40,45),('screen_context',45,50),('cliff_reveal',49,54),('fall_ignition',53,58),('flight_tunnel',56,60)]
if a.start>=0:segments=[('custom_%s_%s'%(a.start,a.end),a.start,a.end)]
if a.stage=='spotlight':segments=[('spotlight',24,29)]
if a.stage=='stills':segments=[('still_%s'%t,t,t+1/12) for t in [22.8,25.5,33.3,37.6,52.3,54.2,57.8]]
s.render.resolution_x=640;s.render.resolution_y=360;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.threads_mode='FIXED';s.render.threads=3
fps=12
if a.stage=='spotlight':
 s.render.engine='BLENDER_EEVEE_NEXT';s.render.resolution_x=480;s.render.resolution_y=270;s.eevee.taa_render_samples=8;s.render.use_compositing=True;fps=8
else:
 s.render.engine='BLENDER_WORKBENCH';s.render.use_compositing=False;sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.show_object_outline=True;sh.object_outline_color=(.003,.003,.012);sh.show_backface_culling=True;sh.background_type='WORLD';s.world.color=(.012,.016,.045);s.display.render_aa='FXAA';s.view_settings.exposure=.65
report=[]
for name,start,end in segments:
 folder=OUT/name;folder.mkdir(exist_ok=True);st=time.time();frames=round((end-start)*fps);qa=[]
 for i in range(frames):
  t=start+i/fps;update(t);bpy.context.view_layer.update();center=hero.matrix_world@Vector((0,0,.65));proj=world_to_camera_view(s,cam,center);direction=center-cam.location
  hit,loc,normal,idx,ob,ma=s.ray_cast(bpy.context.evaluated_depsgraph_get(),cam.location,direction.normalized(),distance=direction.length)
  qa.append({'story_time':t,'hero_center_ndc':[round(v,4) for v in proj],'center_inside_frame':0<proj.x<1 and 0<proj.y<1 and proj.z>0,'first_object_on_camera_to_hero':ob.name if hit else None})
  dest=folder/('%04d.png'%i);s.render.filepath=str(dest);bpy.ops.render.render(write_still=True)
  (PROD/'repair_progress.json').write_text(json.dumps({'pid':os.getpid(),'segment':name,'frame':i+1,'total':frames,'story_time':t,'fps':fps,'resolution':[s.render.resolution_x,s.render.resolution_y]}))
 (folder/'camera_qa.json').write_text(json.dumps(qa,indent=2))
 row={'name':name,'start':start,'end':end,'fps':fps,'frames':frames,'seconds_to_render':round(time.time()-st,2),'folder':str(folder),'engine':s.render.engine};report.append(row);print('SEGMENT_DONE',json.dumps(row),flush=True);(PROD/('repairs_'+a.stage+'.json')).write_text(json.dumps(report,indent=2))
