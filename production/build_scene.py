import bpy, math, random, os, sys, json, time, argparse
from mathutils import Vector
from pathlib import Path
P=Path('/workspace/stray'); OUT=P/'previews'; PROD=P/'production'
random.seed(61)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ap=argparse.ArgumentParser();ap.add_argument('--mode',default='build');ap.add_argument('--asset-mode',default='proxy');ap.add_argument('--asset-file',default='');ap.add_argument('--start',type=int,default=0);ap.add_argument('--end',type=int,default=720);a=ap.parse_args(args)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for d in list(bpy.data.materials): bpy.data.materials.remove(d)
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT';s.render.fps=60;s.frame_start=1;s.frame_end=3600
s.render.resolution_x=1920;s.render.resolution_y=1080;s.render.resolution_percentage=100
s.world.color=(.11,.11,.16);s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.035,.045,.12,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.65
s.view_settings.view_transform='Standard';s.view_settings.look='Medium High Contrast';s.render.image_settings.file_format='PNG';s.render.film_transparent=False
s.render.threads_mode='FIXED';s.render.threads=int(os.environ.get('STRAY_THREADS','3'))
s.eevee.taa_render_samples=32;s.render.image_settings.color_mode='RGB'
M={}
def mat(n,c,emit=0,metal=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=.4;p.inputs['Metallic'].default_value=metal
 if emit:p.inputs['Emission Color'].default_value=(*c,1);p.inputs['Emission Strength'].default_value=emit
 m.use_backface_culling=(n=='glass')
 M[n]=m;return m
for n,c,e in [('ink',(.006,.009,.026),0),('road',(.016,.026,.065),0),('building',(.025,.028,.085),0),('building2',(.055,.028,.11),0),('cyan',(.01,.8,1),2),('pink',(1,.015,.23),2),('yellow',(1,.76,.02),2),('violet',(.39,.06,1),1.5),('white',(.55,.83,.95),.3),('police_white',(.55,.65,.72),0),('red',(1,.01,.025),2),('glass',(.025,.18,.27),0),('fire',(1,.17,.015),2),('smoke',(.19,.035,.3),0),('silver',(.17,.25,.34),0)]:mat(n,c,e,.3 if n=='silver' else 0)
# Mesh helpers, static boxes batched per material
batch={}
def box(n,loc,dim,m='ink',parent=None,bevel=0,batchit=False):
 if batchit:
  v,f=batch.setdefault(m,([],[]));idx=len(v);x,y,z=loc;dx,dy,dz=[d/2 for d in dim]
  v.extend([(x+u*dx,y+w*dy,z+q*dz) for u,w,q in [(-1,-1,-1),(-1,-1,1),(-1,1,-1),(-1,1,1),(1,-1,-1),(1,-1,1),(1,1,-1),(1,1,1)]]);f.extend([tuple(idx+j for j in reversed(face)) for face in [(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3),(0,2,3,1),(4,5,7,6)]]);return
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=n;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(M[m])
 if parent:o.parent=parent
 if bevel:b=o.modifiers.new('edge glints','BEVEL');b.width=bevel;b.segments=2;o.modifiers.new('normals','WEIGHTED_NORMAL')
 return o
def mesh(n,v,f,m,parent=None):
 d=bpy.data.meshes.new(n);d.from_pydata(v,[],f);d.materials.append(M[m]);o=bpy.data.objects.new(n,d);s.collection.objects.link(o)
 if parent:o.parent=parent
 return o
def rod(n,p,q,r,m,parent=None,vertices=8):
 p,q=Vector(p),Vector(q);d=q-p;bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=d.length,location=(p+q)/2);o=bpy.context.object;o.name=n;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();o.data.materials.append(M[m]);o.parent=parent;return o
def empty(n):o=bpy.data.objects.new(n,None);s.collection.objects.link(o);return o
def ico(n,loc,scale,m,parent=None):
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=1,location=loc);o=bpy.context.object;o.name=n;o.scale=scale;o.data.materials.append(M[m]);o.parent=parent;return o
# Avatar placeholders ONLY, assets integrated separately.
def vehicle(n,police=False):
 root=empty(n);body=box(n+'_body',(0,0,.6),(2,4.7,.65),'police_white' if police else 'ink',root,.2)
 # sculpted wedge and clean canopy
 mesh(n+'_canopy',[(-.76,-1,.85),(.76,-1,.85),(-.65,-.5,1.42),(.65,-.5,1.42),(-.68,1.08,.92),(.68,1.08,.92)],[(0,1,3,2),(2,3,5,4),(0,2,4),(1,5,3)],'glass',root)
 for x in [-1,1]:
  for y in [-1.45,1.4]:
   rod(n+'_wheel',(x-.15,y,.4),(x+.15,y,.4),.4,'ink',root,16);rod(n+'_rim',(x-.17,y,.4),(x+.17,y,.4),.24,'silver',root,12)
  box('headlight',(x*.72,2.37,.65),(.46,.045,.09),'white',root)
  box('side accent',(x*1.01,-.2,.51),(.04,2.9,.045),'cyan',root)
  box('tail',(x*.7,-2.36,.7),(.49,.04,.08),'red',root)
 box('dashboard',(0,.7,.79),(1.55,.42,.17),'ink',root)
 box('front blade',(0,2.42,.3),(2.12,.22,.08),'silver',root)
 box('rear wing',(0,-1.9,1.15),(2.2,.38,.1),'ink',root)
 if police:
  box('lightbar',(0,-.2,1.52),(1.35,.35,.12),'ink',root)
  box('blue strobe',(-.4,-.2,1.61),(.52,.3,.15),'cyan',root);box('red strobe',(.4,-.2,1.61),(.52,.3,.15),'red',root)
  for x in [-1.015,1.015]:
   box('police blue door',(x,0,.76),(.02,1.5,.37),'white',root)
   # physical door inscription
   cu=bpy.data.curves.new('POLICE','FONT');cu.body='POLICE';cu.size=.27;cu.extrude=.001;cu.align_x='CENTER';o=bpy.data.objects.new('POLICE door',cu);s.collection.objects.link(o);o.parent=root;o.location=(x*1.004,.2,.66);o.rotation_euler=(math.pi/2,0,math.pi/2 if x<0 else -math.pi/2);o.data.materials.append(M['ink'])
 return root
hero=vehicle('Hero_PROXY');police=[vehicle('Police_PROXY_%d'%i,True) for i in range(3)]
traffic=[vehicle('Traffic_PROXY_%02d'%i) for i in range(12)]
heli=empty('Heli_PROXY');ico('fuselage',(0,0,0),(1.7,3,1.3),'ink',heli);ico('heli cockpit',(0,1.8,.1),(1.4,1.3,.9),'glass',heli);rod('tail',(0,-2,.2),(0,-7,.8),.3,'ink',heli);box('tail fin',(0,-6.8,1.6),(.2,1.3,2),'police_white',heli)
rotor=empty('Rotor');rotor.parent=heli;rotor.location=(0,0,1.7)
for angle in [0,math.pi/2]:o=box('rotor blade',(0,0,0),(11,.2,.055),'silver',rotor);o.rotation_euler.z=angle
for x in [-1.4,1.4]:rod('skid',(x,-2,-1.6),(x,2,-1.6),.09,'silver',heli)
truck=empty('Truck_PROXY');box('truck cab',(0,3.9,1.5),(2.5,2.3,2.7),'yellow',truck,.12);rod('tank',(0,-3,2),(0,2.7,2),1.45,'silver',truck,20)
for x in [-1.25,1.25]:
 for y in [-2.7,-1.7,3.8]:rod('truck wheel',(x-.2,y,.5),(x+.2,y,.5),.5,'ink',truck,12)
# City actual continuous avenue; end cliff and flight canyon
box('avenue approach',(0,315,-.25),(28,670,.5),'road',batchit=True)
box('avenue exit',(0,970,-.25),(28,340,.5),'road',batchit=True)
for side in [-1,1]:box('sidewalk',(side*16,560,-.05),(4,1140,.4),'building',batchit=True)
for y in range(-20,1135,9):
 for x in [-.15,-7,7]:box('lane dash',(x,y,.025),(.12,3,.02),'yellow' if x==-.15 else 'white',batchit=True)
for side in [-1,1]:
 for j,y in enumerate(range(-15,1510,21)):
  x=side*random.uniform(24,34);h=random.uniform(25,80);w=random.uniform(12,20);d=random.uniform(14,20)
  box('tower',(x,y,h/2-1),(w,d,h),'building' if j%2 else 'building2',batchit=True)
  box('roof rim',(x,y,h),(w+.3,d+.3,.25),'violet' if j%3==0 else 'ink',batchit=True)
  for zz in range(3,int(h)-2,4):
   for yy in range(-5,8,4):
    if random.random()<.5:box('lit window',(x-side*w/2-.03,y+yy,zz),(.06,1.5,1.2),random.choice(['cyan','pink','yellow','violet']),batchit=True)
  # building contour ink and graphic cross hatching by actual strips
  for edge in [-1,1]:box('ink edge',(x-side*w/2-.05,y+edge*d/2,h/2),(.1,.14,h),'ink',batchit=True)
  if j%2==0:
   m=random.choice(['cyan','pink','violet']);box('sign backing',(side*18.3,y,12),(1.1,9,8),'ink',batchit=True);box('ad placeholder graphic',(side*17.7,y,12),(.08,8.5,7.4),m,batchit=True)
   for z in [10,12,14]:box('abstract ad stripe',(side*17.63,y,z),(.1,5.5,.22),'yellow',batchit=True)
  # wet vertical-light reflections, deliberate straight graphic strips (not grain)
  for k in range(4):box('wet reflection',(side*random.uniform(8,13),y+random.uniform(-4,4),.033),(random.uniform(.05,.3),random.uniform(2,10),.01),random.choice(['cyan','pink','violet']),batchit=True)
# alley foreground walls only y<22, narrow and clear mouth
for x in [-4.7,4.7]:box('alley wall',(x,1,8),(2,37,16),'building',batchit=True)
for x in [-3.65,3.65]:
 for y in [-10,0,10]:box('alley neon',(x,y,5),(.06,4,.18),'pink' if x<0 else 'cyan',batchit=True)
# Manhattan rooftop water towers and fire escapes graphic silhouette
for side in [-1,1]:
 for y in range(80,1100,130):
  rod('water tank',(side*23,y,46),(side*23,y,50),2.0,'ink',vertices=12)
  for z in range(6,30,5):box('fire escape',(side*17.8,y,z),(2,6,.1),'silver',batchit=True)
# 3D ground signage at intersections and cross streets
for y in [150,370,590,810]:
 box('cross street',(0,y,-.2),(160,22,.35),'road',batchit=True)
 for yy in [-8,8]:
  for x in range(-12,13,2):box('zebra',(x,y+yy,.04),(1.1,3,.02),'white',batchit=True)
# flush static batches
for m,(v,f) in batch.items():mesh('CITY_'+m,v,f,m)
# dynamic props ramps, debris, explosions
ramps=[]
for y in [25,365]:
 o=mesh('instant holographic ramp',[(-1.6,y-5,.06),(1.6,y-5,.06),(-1.6,y+3,2.8),(1.6,y+3,2.8)],[(0,1,3,2)],'cyan');ramps.append(o)
 for i in range(8):rod('ramp rung',(-1.6,y-5+i,.08+i*.34),(1.6,y-5+i,.08+i*.34),.025,'yellow',o)
barriers=[]
for x in [-10,-6,-2,2,6,10]:
 o=box('police barrier',(x,590,.9),(3.8,.65,1.8),'police_white');barriers.append(o)
 for z in [.4,1,1.5]:box('barrier yellow stripe',(0,-.34,z-.9),(3.4,.025,.1),'yellow',o)
# foldable street physically becomes elevated overhead curl
curl=[]
for i in range(22):
 y=650+i*7;o=box('folding road slab %02d'%i,(0,y,-.18),(25,6.98,.35),'road');curl.append(o)
 box('slab cyan edge',(-12.3,0,.19),(.1,6.9,.025),'cyan',o);box('slab pink edge',(12.3,0,.19),(.1,6.9,.025),'pink',o)
takeover_lane=box('network takeover safe lane',(0,726,.025),(3.8,155,.05),'cyan')
# light ribbon curve, continuous at path entry and exit
rv=[];rf=[]
def ringpos(u):return Vector((18*math.sin(u*2*math.pi)*math.sin(u*math.pi)**2,850+190*u,1+23*(1-math.cos(u*2*math.pi))))
for i in range(161):
 p=ringpos(i/160);rv.extend([tuple(p+Vector((-3,0,0))),tuple(p+Vector((3,0,0)))])
 if i:rf.append((2*i-2,2*i-1,2*i+1,2*i))
mesh('raised circular road light ribbon',rv,rf,'violet')
for side in [-1,1]:
 for i in range(160):
  p=ringpos(i/160)+Vector((3*side,0,.12));q=ringpos((i+1)/160)+Vector((3*side,0,.12));rod('ring edge',p,q,.065,'cyan' if side<0 else 'pink')
# screen: thousands not needed, 24 shards actual fracture panels
screen=[]
for ix in range(8):
 for iz in range(4):
  o=box('billboard break shard',(-10.5+ix*3,1048,2+iz*3),(2.96,.18,2.96),'pink' if (ix+iz)%2 else 'cyan');screen.append((o,o.location.copy()))
for x in [-13,13]:rod('billboard frame',(x,1048,0),(x,1048,17),.22,'ink')
# cliff gap absolutely no road past y1140, canyon buildings frame flight
for x in [-21,21]:box('cliff exposed edge',(x,1135,-12),(14,10,24),'building')
# end-of-canyon light, actual distant object
box('canyon end light',(0,1470,28),(12,.4,37),'cyan')
# interior holographic dashboard attached hero, independent overlay in true 3D
maproot=empty('holographic street takeover');maproot.parent=hero;maproot.location=(0,1.2,1.2);maproot.rotation_euler.x=1.1
for x in [-.6,-.3,0,.3,.6]:rod('map road',(x,-.4,0),(x,.6,0),.012,'cyan',maproot)
for y in [-.4,-.1,.2,.5]:rod('map cross street',(-.7,y,0),(.7,y,0),.012,'pink',maproot)
# stylized effects persistent fixed-origin physical events
fx=[]
for origin,start in [((1,370,1.5),22.5),((0,715,-5),39.2)]:
 cloud=[]
 for i in range(21):
  v=Vector((random.uniform(-1,1),random.uniform(-1,1),random.uniform(.1,1.5)));o=ico('inked comic blast',origin,(1,1,1),random.choice(['fire','yellow','pink','smoke']));cloud.append((o,v,random.uniform(.6,1.5)))
 fx.append((Vector(origin),start,cloud))
debris=[]
for i in range(32):
 o=box('barrier flying debris',(0,0,-100),(.3,.25,.45),'white' if i%2 else 'yellow');debris.append((o,Vector((random.uniform(-8,8),random.uniform(5,16),random.uniform(2,8)))))
flames=[]
for x in [-.6,.6]:
 o=ico('rocket flat flame',(x,-3.1,.55),(.2,1.2,.25),'fire',hero);flames.append(o)
for x in [-.7,.7]:
 o=ico('undercarriage cold jet',(x,0,-.8),(.22,.3,1),'cyan',hero);flames.append(o)
# helicopter searchlight cone is mesh, not expensive volume
beam=mesh('searchlight cone',[(-.1,0,-1),(0,0,-1),(0,.1,-1),(-4,3,-16),(4,3,-16),(0,-4,-16)],[(0,3,4,1),(1,4,5,2),(2,5,3,0)],'white',heli);beam.hide_render=True
# light pool physically follows helicopter
pool=ico('helicopter light on wet road',(0,0,.04),(4,6,.025),'white')
# rain as genuine 3D line segments (single mesh), no grain
rainseeds=[(random.uniform(-35,35),random.uniform(-20,100),random.uniform(0,35)) for i in range(900)]
rain=mesh('world rain',[p for x,y,z in rainseeds for p in [(x,y,z),(x-.025,y-.06,z-.6)]],[],'white');rain.data.edges.add(900);rain.data.edges.foreach_set('vertices',[j for i in range(900) for j in (i*2,i*2+1)])
# edges are not rendered by Eevee, use slender triangles
bpy.data.objects.remove(rain,do_unlink=True)
rain=mesh('graphic rain geometry',[(x+dx,y,z+dz) for x,y,z in rainseeds for dx,dz in [(0,0),(.012,0),(-.03,-.55)]],[(3*i,3*i+1,3*i+2) for i in range(900)],'white')
# lighting
for loc,power,color,size in [((0,0,35),2200,(.12,.45,1),25),((-8,10,8),1600,(1,.02,.15),10),((6,-4,6),1800,(.04,1,1),8)]:
 d=bpy.data.lights.new('hero moving softbox','AREA');d.energy=power;d.use_shadow=False;d.color=color;d.shape='DISK';d.size=size;o=bpy.data.objects.new(d.name,d);s.collection.objects.link(o);o.parent=hero;o.location=loc;o.rotation_euler=(Vector((0,0,.4))-Vector(loc)).to_track_quat('-Z','Y').to_euler()
d=bpy.data.lights.new('night broad key','SUN');d.energy=1.5;d.color=(.3,.36,.7);o=bpy.data.objects.new('night broad key',d);s.collection.objects.link(o);o.rotation_euler=(.4,-.4,-.5)
camd=bpy.data.cameras.new('ONE continuous camera');cam=bpy.data.objects.new('ONE continuous camera',camd);s.collection.objects.link(cam);s.camera=cam;camd.lens=32;camd.clip_end=280;camd.clip_start=.03
# compositor gentle glow only, no grain/global chromatic aberration
s.use_nodes=True;nt=s.node_tree;nt.nodes.clear();rl=nt.nodes.new('CompositorNodeRLayers');gl=nt.nodes.new('CompositorNodeGlare');gl.glare_type='FOG_GLOW';gl.quality='LOW';gl.threshold=1.2;gl.size=7;co=nt.nodes.new('CompositorNodeComposite');nt.links.new(rl.outputs['Image'],gl.inputs[0]);nt.links.new(gl.outputs[0],co.inputs[0])
# Animation definitions 60s, smooth actual 3D path.
def smooth(u):u=max(0,min(1,u));return u*u*(3-2*u)
def interp(keys,t):
 if t<=keys[0][0]:return Vector(keys[0][1])
 for i in range(len(keys)-1):
  t0,p=keys[i];t1,q=keys[i+1]
  if t<=t1:return Vector(p).lerp(Vector(q),smooth((t-t0)/(t1-t0)))
 return Vector(keys[-1][1])
# Hermite spline keeps y motion without stop/start at every beat.
keys=[(0,(0,0,0)),(3.7,(0,0,0)),(5.8,(0,15,0)),(6.8,(0,25,4)),(8.8,(0,32,5)),(10.285714,(0,57,0)),(13,(-4,125,0)),(16,(4,218,0)),(19,(-3,301,0)),(20.8,(0,351,0)),(22.2,(0,373,6)),(23.6,(0,405,3)),(24.5,(0,431,0)),(29,(0,565,0)),(30,(0,590,0)),(33,(0,652,0)),(37,(0,727,0)),(40,(0,800,0)),(42,(0,850,1)),(49,(0,1040,1)),(50,(0,1060,0)),(52,(0,1120,0)),(53,(0,1143,-2)),(54.5,(0,1158,-12)),(56,(0,1205,7)),(60,(0,1380,24))]
def carpos(t):
 if 42<t<49:return ringpos((t-42)/7)
 if t<=0:return Vector(keys[0][1])
 for i in range(len(keys)-1):
  t0,p=keys[i];t1,q=keys[i+1]
  if t<=t1:
   u=(t-t0)/(t1-t0);p,q=Vector(p),Vector(q)
   before=keys[max(0,i-1)];after=keys[min(len(keys)-1,i+2)]
   m0=(q-Vector(before[1]))/(t1-before[0]) if t1>before[0] else Vector((0,0,0));m1=(Vector(after[1])-p)/(after[0]-t0) if after[0]>t0 else Vector((0,0,0))
   if i<1:m0=Vector((0,0,0));m1=Vector((0,0,0))
   return (2*u**3-3*u*u+1)*p+(u**3-2*u*u+u)*m0*(t1-t0)+(-2*u**3+3*u*u)*q+(u**3-u*u)*m1*(t1-t0)
 return Vector(keys[-1][1])
camkeys=[(0,(-2.4,-13,2.6)),(3.7,(-1.5,-11,2.2)),(5.8,(-2,-8,3)),(6.8,(-2,4,3.5)),(7.2,(-8,2,5)),(7.7,(-10,-5,5)),(10.3,(-6,-8,2.2)),(14,(-6,6,2.3)),(19,(-9,9,3)),(22,(-17,-19,8)),(23.5,(-17,-45,8)),(24.6,(-13,-13,8)),(27,(-13,-13,8)),(30,(-3,11,2)),(31.5,(-2,3.7,1.45)),(32.3,(-.55,.9,1.2)),(33,(0,.05,1.1)),(35,(0,.05,1.1)),(36,(-1,4,1.3)),(38,(-11,-10,5)),(40,(-11,12,6)),(42,(-10,-9,6)),(46,(-13,-7,6)),(49,(-10,-7,5)),(51,(-10,-10,12)),(53,(-9,-4,4)),(54.5,(-8,3,5)),(56,(-7,-10,4)),(60,(-5,-15,5))]
def worldtime(t):
 r=t
 for lo,hi,speed in [(6.8,8.8,.18),(47.3,49,.3),(53,54.5,.35)]:r-=(1-speed)*max(0,min(t,hi)-lo)
 return r
def visible(o,on):
 o.hide_render=not on;o.hide_viewport=not on
 for child in o.children:visible(child,on)
# cache base positions for destructive object transforms
basebar=[o.location.copy() for o in barriers]

def update(t):
 p=carpos(t);hero.location=p;visible(takeover_lane,32<t<42)
 for i,o in enumerate(traffic):o.location=((i%3-1)*6,90+i*26+t*6,0)
 tangent=carpos(min(60,t+.015))-carpos(max(0,t-.015));hero.rotation_euler=(math.atan2(tangent.z,max(.01,tangent.y)),0,-math.atan2(tangent.x,max(.01,tangent.y)))
 for o in hero.children:
  if o.name.startswith('Hero_Wheel_'):o.rotation_euler.x=-p.y/.34
 cam.location=p+interp(camkeys,t)
 if 31.8<t<35.7:target=p+Vector((0,8,1.2))
 else:target=p+Vector((0,2 if t>50 else 0,.8))
 # blend gaze to windshield seamlessly
 blend=smooth((t-30.5)/1.3)*(1-smooth((t-35.7)/1.3));target=target.lerp(p+Vector((0,8,1.2)),blend)
 if 21<t<24.5:target=target.lerp(Vector((0,370+(p.y-370)*.55,3)),smooth((t-21)/.7)*(1-smooth((t-23.8)/.7)))
 if 23<t<29:target=target.lerp(p+Vector((2,6,5)),smooth((t-23)/1.2)*(1-smooth((t-27.8)/1.2)))
 if 36<t<39.2:target=target.lerp(p+Vector((0,12,8)),smooth((t-36)/1)*(1-smooth((t-38.2)/1)))
 if 50<t<54:target=target.lerp(p+Vector((0,30,-2)),smooth((t-50)/.8)*(1-smooth((t-53.2)/.8)))
 cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camd.lens=48-16*smooth((t-3)/1.5)-5*smooth((t-23.5)/1)*(1-smooth((t-27.5)/1))-6*smooth((t-20.5)/1)*(1-smooth((t-23.5)/1))
 for i,o in enumerate(police):
  if t<6:
   o.location=( (-11 if i==0 else 11)*(1-smooth((t-1.4)/2.4))+(-1.7 if i==0 else 1.7)*smooth((t-1.4)/2.4),25,0);o.rotation_euler=(0,0,math.pi/2 if i<2 else 0);visible(o,True)
   if i==2:o.location=(0,-35,0);o.rotation_euler=(0,0,0)
  else:
   delay=[.65,1.05,1.45][i];q=carpos(max(0,t-delay));q.z=0 if t<42 else q.z;q.x+=(-2 if i==0 else 2 if i==1 else 0);o.location=q;o.rotation_euler=hero.rotation_euler;visible(o,True)
   if t<10:
    start=Vector((-1.7 if i==0 else 1.7 if i==1 else 0,25 if i<2 else -35,0));o.location=start.lerp(q,smooth((t-6)/4));o.rotation_euler.z=(math.pi/2)*(1-smooth((t-6)/1.5)) if i<2 else 0
   if i==0 and 21.8<t<=22.5:o.location=q.lerp(Vector((1,370,0)),smooth((t-21.8)/.7))
   if i==0 and t>22.5:o.location=(1,370,-max(0,t-22.5)*1.5);o.rotation_euler=(0,(t-22.5)*1.3,0)
   if i==1 and t>38.7:o.location=carpos(37.65)+Vector((2,0,-(t-38.7)**2*3));o.rotation_euler=((t-38.7),0,.6)
   if i==2 and t>49.8:visible(o,False)
 truck.location=(18*(1-smooth((t-19)/3.5)),370,0);truck.rotation_euler.z=math.pi/2
 heli.location=(p.x+4,p.y+12,11+math.sin(t*.3));rotor.rotation_euler.z=worldtime(t)*26;pool.location=(heli.location.x,heli.location.y,.06);visible(heli,True);visible(beam,False);visible(pool,24<t<41)
 for i,r in enumerate(ramps):visible(r,(5.3<t<9.7) if i==0 else (20<t<23.8))
 for i,o in enumerate(barriers):
  dt=max(0,t-30);o.location=basebar[i]+Vector(((i-2.5)*dt*1.5,dt*15,dt*6-dt*dt*4));o.rotation_euler=(dt*2,dt,dt*.5)
 for i,o in enumerate(curl):
  theta=smooth((t-35-i*.045)/3)*min(math.pi*1.35,(i/21)*math.pi*1.35);radius=29
  u=smooth((t-35-i*.045)/3);o.location=Vector((0,650+i*7,-.18)).lerp(Vector((0,800-radius*math.sin(theta),radius*(1-math.cos(theta))-.18)),u);o.rotation_euler.x=theta
 for o,base in screen:
  dt=max(0,t-49.2);o.location=base+Vector(((base.x)*dt*.7,dt*14,dt*(base.z-5)*.5-dt*dt*3));o.rotation_euler=(dt*.6,dt*.7,dt*.3)
 for origin,start,cloud in fx:
  if start==39.2:origin=carpos(37.65)+Vector((2,0,-5))
  dt=math.floor((t-start)*30)/30
  for o,v,sz in cloud:
   visible(o,0<dt<3.8);o.location=origin+v*max(0,dt)*5;size=max(.01,math.sin(min(1,max(0,dt/3.8))*math.pi)*sz*4);o.scale=(size,size*.8,size)
 for o,v in debris:
  dt=max(0,t-30);visible(o,0<dt<2);o.location=Vector((0,590,1))+v*dt+Vector((0,0,-5*dt*dt));o.rotation_euler=(dt*3,dt*2,dt)
 for i,o in enumerate(flames):visible(o,(21<t<24 or t>54.5) if i<2 else t>54.5)
 visible(maproot,32<t<36)
 # effect quantization only, hero/camera positions are not quantized
 wt=worldtime(math.floor(t*30)/30);verts=[]
 for x,y,z in rainseeds:
  zz=(z-wt*11)%35;yy=y+p.y-10
  verts.extend([(x,yy,zz),(x+.012,yy,zz),(x-.03,yy,zz-.55)])
 rain.data.vertices.foreach_set('co',[v for p0 in verts for v in p0]);rain.data.update()
 # final graceful fade via world transparent film not black flash; compositor multiply
 return p

# optional asset append once available; proxy pipeline never overwrites Codex
if a.asset_mode=='codex':
 asset=Path(a.asset_file) if a.asset_file else P/'assets/codex/assets.blend'
 if not asset.exists():raise FileNotFoundError('Codex assets not ready; use --asset-mode proxy explicitly')
 oldhero=hero
 with bpy.data.libraries.load(str(asset),link=False) as (data_from,data_to):data_to.collections=['Hero']
 for c in data_to.collections:
  if c:s.collection.children.link(c)
 hero=bpy.data.objects.get('Hero_Root')
 if hero is None:raise RuntimeError('Appended Hero_Root missing')
 # Move shot-owned FX/lighting to replacement root; do not modify source asset file.
 for o in [maproot,*flames,*[c for c in list(oldhero.children) if c.type=='LIGHT']]:o.parent=hero
 visible(oldhero,False)
 for o in hero.children_recursive:
  if o.type=='MESH':
   for m in o.data.materials:
    if m and 'glass' in m.name.lower():m.use_backface_culling=True
 print('CODEX HERO INTEGRATED',len(hero.children_recursive),'objects',flush=True)

update(7.8);bpy.ops.wm.save_as_mainfile(filepath=str(PROD/('stray_integrated_snapshot.blend' if a.asset_mode=='codex' else 'stray_proxy_scene.blend')))
manifest={'duration':60,'final_fps':60,'preview_fps':12,'preview_resolution':[640,360],'status':a.asset_mode+' animatic; not final','events':{'jump':7.8,'drop_landing':10.285714,'tanker_collision':22.5,'barrier':30,'cockpit':33.5,'road_curl':37,'ring':46,'screen':49.2,'cliff_fall':54,'flight':56},'assets':a.asset_mode,'asset_file':a.asset_file,'scene_note':'Snapshot only; motion is evaluated procedurally by update(t) in this script, not baked timeline keys'}
(PROD/'manifest.json').write_text(json.dumps(manifest,indent=2))
if a.mode in ['test','testfull']:
 s.render.resolution_x=1920 if a.mode=='testfull' else 640;s.render.resolution_y=1080 if a.mode=='testfull' else 360;s.eevee.taa_render_samples=32
 times=[]
 for t in ([22.4] if a.mode=='testfull' else [4.5,22.4,46]):
  update(t);s.render.filepath=str(OUT/(('fullbench_' if a.mode=='testfull' else 'codex_test_' if a.asset_mode=='codex' else 'test_')+'%05.2fs.png'%t));st=time.time();bpy.ops.render.render(write_still=True);times.append({'time':t,'seconds':time.time()-st,'path':s.render.filepath});(PROD/('benchmark1080.json' if a.mode=='testfull' else 'benchmark.json')).write_text(json.dumps(times,indent=2));print('BENCHMARK',times[-1],flush=True)
elif a.mode=='animatic':
 s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=640;s.render.resolution_y=360;s.render.resolution_percentage=100;s.display.shading.light='STUDIO';s.display.shading.studiolight_rotate_z=.5;s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.show_backface_culling=True;s.display.shading.show_object_outline=True;s.display.shading.object_outline_color=(.005,.005,.015);s.display.shading.background_type='WORLD';s.world.color=(.012,.016,.045);s.display.render_aa='FXAA';s.render.use_compositing=False;s.view_settings.exposure=.6
 frames=OUT/('animatic_frames_codex' if a.asset_mode=='codex' else 'animatic_frames_v3');frames.mkdir(exist_ok=True)
 start=time.time()
 for i in range(a.start,a.end):
  dest=frames/('%05d.png'%i)
  if dest.exists() and dest.stat().st_size>100:
   with open(dest,'rb') as fh:fh.seek(-8,2);valid=fh.read()==b'IEND\xaeB`\x82'
   if valid:continue
  update(i/12);s.render.filepath=str(dest);st=time.time();bpy.ops.render.render(write_still=True)
  (PROD/'progress.json').write_text(json.dumps({'mode':a.asset_mode+'_workbench_animatic','frame':i+1,'total':720,'seconds_of_story':round(i/12,3),'last_frame_seconds':round(time.time()-st,3),'elapsed':round(time.time()-start,1),'pid':os.getpid()}));print('PROGRESS',i+1,720,'seconds',round(time.time()-st,2),flush=True)
