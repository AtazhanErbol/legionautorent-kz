"""Build an original web hero sedan in Blender 4.5; coordinates below use glTF axes.

blender --background --factory-startup --python tools/build_hero_sedan.py
All output goes to assets/hero-sedan. Existing production assets are never overwritten.
"""
import bpy, math, json, hashlib
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets'/'hero-sedan'
OUT.mkdir(parents=True,exist_ok=True)
PI=math.pi
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# x = car left, y = height, z = front. Blender exports +Z up to glTF +Y up.
def V(p): return (p[0],-p[2],p[1])
def add(a,b): return tuple(a[i]+b[i] for i in range(3))
def mix(a,b,t): return tuple(a[i]*(1-t)+b[i]*t for i in range(3))
def smooth(t): return t*t*(3-2*t)
def interp(points,t):
    for i,((a,x),(b,y)) in enumerate(zip(points,points[1:])):
        if a<=t<=b:
            # Nonuniform cubic Hermite: continuous slopes avoid highlight ripples.
            prev=points[max(0,i-1)];nxt=points[min(len(points)-1,i+2)]
            m0=(y-prev[1])/(b-prev[0]);m1=(nxt[1]-x)/(nxt[0]-a)
            f=(t-a)/(b-a);d=b-a
            return (2*f**3-3*f*f+1)*x+(f**3-2*f*f+f)*d*m0+(-2*f**3+3*f*f)*y+(f**3-f*f)*d*m1
    return points[0][1] if t<points[0][0] else points[-1][1]

car=bpy.data.collections.new('LEGION_SEDAN')
bpy.context.scene.collection.children.link(car)
def to_car(obj):
    for c in list(obj.users_collection): c.objects.unlink(obj)
    car.objects.link(obj)

def material(name,color,metal=0,rough=.4,alpha=1,coat=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,alpha);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,alpha)
    p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    p.inputs['Alpha'].default_value=alpha;p.inputs['Coat Weight'].default_value=coat
    p.inputs['Coat Roughness'].default_value=.16
    if alpha<1:m.surface_render_method='DITHERED'
    return m

paint=material('Body_Paint',(.020,.024,.030),.8,.205,coat=.55)
glass=material('Glass',(.010,.019,.027),.5,.16,coat=.45)
black=material('Black_Plastic',(.009,.011,.014),.14,.35)
rubber=material('Tire',(.014,.016,.019),0,.66)
rim=material('Rim',(.20,.23,.27),.92,.24)
chrome=material('Satin_Aluminium',(.46,.50,.54),.96,.2)
brake=material('Brake_Disc',(.16,.175,.185),.85,.43)
caliper=material('Brake_Caliper',(.07,.078,.09),.7,.28)
darkmetal=material('Dark_Metal',(.034,.043,.055),.83,.31)
interior=material('Interior',(.017,.022,.027),0,.75)
frontled=material('Headlight_Lens',(.42,.50,.59),.22,.17)
rearled=material('Taillight_Lens',(.26,.002,.006),.12,.2)
redlens=material('Taillight_Cover',(.15,.002,.004),.3,.16,coat=.5)
clear=material('Lamp_Cover',(.025,.045,.065),.45,.1,coat=.6)
seammat=material('Panel_Gaps',(.002,.003,.004),0,.8)

def mesh(name,verts,faces,mat,smooth_shading=True):
    data=bpy.data.meshes.new(name);data.from_pydata([V(p) for p in verts],[],faces);data.update()
    obj=bpy.data.objects.new(name,data);car.objects.link(obj)
    data.materials.append(mat)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    for p in data.polygons:p.use_smooth=smooth_shading
    return obj

def grid(name,fn,nu,nv,mat):
    verts=[fn(i/nu,j/nv) for i in range(nu+1) for j in range(nv+1)]
    faces=[]
    for i in range(nu):
        for j in range(nv):
            a=i*(nv+1)+j;faces.append((a,a+1,a+nv+2,a+nv+1))
    return mesh(name,verts,faces,mat)

def empty(name,loc=(0,0,0)):
    obj=bpy.data.objects.new(name,None);car.objects.link(obj);obj.location=V(loc);return obj

def parent(obj,p):
    world=obj.matrix_world.copy();obj.parent=p;obj.matrix_world=world;return obj

def tube(name,points,radius,mat,sides=6,closed=False):
    # Small explicit tubes export without curve tessellation surprises.
    verts=[];n=len(points)
    for i,p in enumerate(points):
        prev=Vector(points[(i-1)%n] if closed or i else points[0])
        nxt=Vector(points[(i+1)%n] if closed or i<n-1 else points[-1])
        tangent=(nxt-prev).normalized();ref=Vector((0,1,0))
        if abs(tangent.dot(ref))>.95:ref=Vector((1,0,0))
        a=tangent.cross(ref).normalized();b=tangent.cross(a).normalized()
        for j in range(sides):
            q=Vector(p)+radius*(a*math.cos(j*2*PI/sides)+b*math.sin(j*2*PI/sides));verts.append(tuple(q))
    faces=[]
    for i in range(n if closed else n-1):
        for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,((i+1)%n)*sides+(j+1)%sides,((i+1)%n)*sides+j))
    if not closed:faces += [tuple(reversed(range(sides))),tuple((n-1)*sides+j for j in range(sides))]
    return mesh(name,verts,faces,mat)

def box(name,center,size,mat,bevel=.02):
    bpy.ops.mesh.primitive_cube_add(size=1,location=V(center));o=bpy.context.object;o.name=name;to_car(o)
    o.scale=(size[0],size[2],size[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    if bevel:
        m=o.modifiers.new('Edge radii','BEVEL');m.width=bevel;m.segments=3
        bpy.ops.object.modifier_apply(modifier=m.name)
    for p in o.data.polygons:p.use_smooth=True
    mod=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=mod.name);o.select_set(False)
    return o

def ellipsoid(name,center,scale,mat,segments=24,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=V(center))
    o=bpy.context.object;o.name=name;to_car(o);o.scale=(scale[0],scale[2],scale[1]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    o.select_set(False);return o

def width(z):return interp([(-2.48,.86),(-2.15,.948),(-1.46,.974),(-.65,.939),(.5,.939),(1.44,.976),(2.15,.945),(2.48,.895)],z)
def deck(z):return interp([(-2.48,.975),(-2.05,1.055),(-1.45,1.063),(-.7,1.060),(.75,1.070),(1.25,1.061),(2.02,1.018),(2.48,.978)],z)
def skin_h(x,z):
    t=min(1,abs(x)/width(z))
    return deck(z)-.135*(1-math.sqrt(max(0,1-t*t)))
def shoulder(z):return deck(z)-.127
def end_z(x,h,front=True):
    if front:
        center=interp([(.23,2.32),(.34,2.42),(.55,2.48),(.74,2.44),(.85,2.38),(.978,2.29)],h)
        return center-.255*(abs(x)/.91)**2
    center=interp([(.23,2.29),(.40,2.42),(.68,2.46),(.82,2.42),(.975,2.30)],h)
    return -center+.235*(abs(x)/.91)**2
def warp(x,z,h=None):
    if h is None:h=skin_h(x,z)
    blend=min(1,max(0,(abs(z)-1.90)/.58))**2
    return z*(1-blend)+end_z(x,h,z>0)*blend
def side_x(z,h):
    htop=shoulder(z);t=max(0,min(1,(h-.21)/(htop-.21)))
    # Slight concavity below the crisp shoulder and a tucked sill.
    return width(z)-.09*(1-t)**2-.020*math.sin(t*PI)**2
wheel_z=[-1.46,1.44];wheel_h=.371;arch_r=.415
def bottom(z):
    y=.232
    for wz in wheel_z:
        d=z-wz
        if abs(d)<arch_r:y=max(y,wheel_h+math.sqrt(max(0,arch_r*arch_r-d*d)))
    return y

# A continuous shell, with genuinely open wheel arches rather than covered wheels.
stations=sorted(set([-2.48+i*4.96/72 for i in range(73)]+[wz+arch_r*math.cos(PI*i/24) for wz in wheel_z for i in range(25)]))
verts=[];faces=[];n=24
for z in stations:
    for j in range(n+1):
        t=math.sin((-1+2*j/n)*PI/2);x=t*width(z);h=skin_h(x,z)
        verts.append((x,h,warp(x,z)))
for i in range(len(stations)-1):
    for j in range(n):
        a=i*(n+1)+j;faces.append((a,a+1,a+n+2,a+n+1))
body=mesh('Body',verts,faces,paint)
for side in [-1,1]:
    verts=[];faces=[];ns=5
    for z in stations:
        hi=shoulder(z)-.008;lo=bottom(z)
        for j in range(ns+1):
            f=j/ns;h=hi*(1-f)+lo*f;x=side*side_x(z,h);verts.append((x,h,warp(x,z,h)))
    for i in range(len(stations)-1):
        for j in range(ns):
            a=i*(ns+1)+j;faces.append((a,a+1,a+ns+2,a+ns+1))
    mesh('Body_side',verts,faces,paint)
    # Thin painted lips and inset black wheel housings follow the cutout precisely.
    for wz in wheel_z:
        points=[]
        for i in range(65):
            a=PI*i/64;z=wz+arch_r*math.cos(a);h=wheel_h+arch_r*math.sin(a)
            points.append((side*(side_x(z,h)+.002),h,warp(side*width(z),z)))
        tube('Fender_edge',points,.0085,paint,sides=6)
        grid('Arch_liner',lambda u,v,wz=wz,s=side:(s*(.81+.126*v),wheel_h+(.415+.005*v)*math.sin(PI*u),wz+(.415+.005*v)*math.cos(PI*u)),40,2,black)
    # Sills and one subtle shoulder highlight formed by geometry, not white paint.
    tube('Sill',[(side*(side_x(z,.26)+.003),.261,z) for z in [-1.02+i*2.02/32 for i in range(33)]],.018,paint,8)
    tube('Sill_trim',[(side*(side_x(z,.285)+.004),.285,z) for z in [-1.02+i*2.02/24 for i in range(25)]],.004,chrome)
    # The shoulder is a continuous curved skin, without a separate shiny rail.

for sign in [-1,1]:
    z=sign*2.48
    def bumper(u,v,z=z):
        x=(-1+2*u)*width(z);h=skin_h(x,z)*(1-v)+.24*v
        return(x,h,end_z(x,h,z>0))
    grid('Bumper_skin',bumper,40,14,paint)
    tube('Bumper_lower_edge',[(x,.257,end_z(x,.257,z>0)+sign*.006) for x in [-width(z)+2*width(z)*i/40 for i in range(41)]],.012,darkmetal,6)
box('Underbody',(0,.235,0),(1.68,.06,4.5),black,.03)

# Cabin: separate double-curved glass surfaces and continuous arched roof.
def roof_h(z):return interp([(-1.06,1.369),(-.78,1.453),(-.32,1.486),(.12,1.466),(.45,1.392)],z)
def roof_w(z):return interp([(-1.06,.674),(-.7,.719),(0,.724),(.45,.692)],z)
roof=grid('Roof',lambda u,v:((2*v-1)*roof_w(-1.06+1.51*u),roof_h(-1.06+1.51*u)-.039*(2*v-1)**2,-1.06+1.51*u),30,20,paint)
def windshield(u,v):
    t=2*v-1;z=.45+(1.13-.45)*u;w=.692+(.846-.692)*u
    h=(roof_h(.45)-.039*t*t)*(1-u)+(1.064-.026*t*t)*u+.037*math.sin(PI*u)
    return (w*t,h,z+.055*(1-t*t)*math.sin(PI*u))
grid('Glass',windshield,16,26,glass)
def backglass(u,v):
    t=2*v-1;z=-1.06-.65*u;w=.674+.147*u
    h=(roof_h(-1.06)-.039*t*t)*(1-u)+(1.068-.028*t*t)*u+.028*math.sin(PI*u)
    return(w*t,h,z-.017*(1-t*t)*math.sin(PI*u))
grid('Rear_glass',backglass,16,26,glass)
for fn,label in [(windshield,'Windscreen'),(backglass,'Rear_screen')]:
    for u in [0,1]:tube(label+'_seal',[fn(u,j/40) for j in range(41)],.010,black,6)
    for v in [0,1]:tube(label+'_pillar',[fn(j/24,v) for j in range(25)],.017,paint,6)

def window_x(z,h):
    return width(z)-.083-(h-1.014)*.35
def sidepoint(s,z,h,offset=0):return(s*(window_x(z,h)+offset),h,z)
for side in [-1,1]:
    # Four side windows, each with a lightly convex surface.
    for name,ends in [('Front_window',(1.09,-.30,.415,-.27)),('Rear_window',(-.39,-1.53,-.36,-1.025))]:
        def win(u,v,ends=ends,s=side):
            za,zb,ta,tb=ends
            bz=za+(zb-za)*v;tz=ta+(tb-ta)*v
            bottom_h=1.026+max(0,-bz-.5)*.029
            z=bz*(1-u)+tz*u;h=bottom_h*(1-u)+(roof_h(tz)-.072)*u
            return sidepoint(s,z,h,.007*math.sin(PI*u)*math.sin(PI*v))
        grid(name,win,9,16,glass)
        perimeter=[win(0,j/16) for j in range(16)]+[win(j/12,1) for j in range(12)]+[win(1,1-j/16) for j in range(16)]+[win(1-j/12,0) for j in range(12)]
        tube('Window_weatherseal',perimeter,.011,black,6,True)
        tube('Window_brightwork',[(p[0]+side*.005,p[1],p[2]) for p in perimeter],.0025,chrome,5,True)
    # Roof rails / A, B and C pillars, all physical surfaces.
    grid('Roof_side_band',lambda u,v,s=side:mix((s*roof_w(-1.06+1.51*u),roof_h(-1.06+1.51*u)-.039,-1.06+1.51*u),sidepoint(s,-1.06+1.51*u,roof_h(-1.06+1.51*u)-.078),v),40,3,paint)
    bpoly=[sidepoint(side,z,h) for z,h in [(-.305,1.027),(-.27,1.403),(-.35,1.402),(-.395,1.029)]]
    mesh('B_pillar',bpoly,[(0,1,2,3)],black)
    cpoly=[sidepoint(side,z,h) for z,h in [(-1.02,1.342),(-1.54,1.055),(-1.72,1.044),(-1.06,1.352)]]
    mesh('C_pillar',cpoly,[(0,1,2,3)],paint)
    def belt(u,v,s=side):
        z=-1.62+2.75*u;hi=1.026+max(0,-z-.5)*.029;x=window_x(z,hi)
        low=skin_h(x,z)
        return(s*(x+.012*(1-v)),low*(1-v)+hi*v,z)
    grid('Cabin_belt_panel',belt,40,3,paint)
    # Door panel gaps wrap down from the belt without cutting into the wheel arches.
    for coords in [[(1.095,1.005),(1.07,.89),(1.005,.61),(.90,.34),(.72,.316),(-.30,.316),(-.36,.4),(-.37,.82),(-.35,1.02)], [(-.38,1.025),(-.43,.82),(-.43,.38),(-.55,.314),(-1.00,.314),(-1.03,.56),(-1.19,.81),(-1.49,1.027)]]:
        points=[]
        for (z0,h0),(z1,h1) in zip(coords,coords[1:]):
            for j in range(3):
                t=j/3;z=z0+(z1-z0)*t;h=h0+(h1-h0)*t
                points.append((side*(side_x(z,min(h,shoulder(z)))+.003),h,warp(side*width(z),z,h)))
        tube('Door_seam',points,.0025,seammat,5)
    for z in [-.19,-1.04]:
        x=side*(side_x(z,.934)+.006)
        box('Handle_recess',(x,.932,z),(.009,.026,.19),black,.009)
        box('Door_handle',(x+side*.011,.938,z),(.023,.019,.165),darkmetal,.009)
        box('Handle_edge',(x+side*.024,.941,z),(.007,.005,.137),chrome,.002)
    mirror=empty('Mirror_L' if side==1 else 'Mirror_R')
    parent(tube('Mirror_stem',[(side*.84,1.068,.92),(side*.97,1.059,.83),(side*1.03,1.083,.80)],.028,black,8),mirror)
    parent(ellipsoid('Mirror_shell',(side*1.034,1.105,.825),(.131,.059,.131),paint),mirror)
    parent(ellipsoid('Mirror_lower',(side*1.034,1.08,.818),(.131,.029,.125),black),mirror)
    parent(ellipsoid('Mirror_glass',(side*1.037,1.108,.72),(.103,.038,.009),rim),mirror)
    parent(tube('Mirror_indicator',[(side*(.957+i*.006),1.104,.924) for i in range(27)],.004,frontled,5),mirror)

# Hood shut lines and subtle creases follow the actual compound-curved skin.
for side in [-1,1]:
    points=[];crease=[]
    for i in range(51):
        z=1.105+(2.40-1.105)*i/50;f=(z-1.105)/1.295;x=side*(.67-.115*f)
        points.append((x,skin_h(x,z)+.002,warp(x,z)))
        x2=x-side*.11;crease.append((x2,skin_h(x2,z)+.002,warp(x2,z)))
    tube('Hood_gap',points,.0024,seammat,5);tube('Hood_sculpt',crease,.0045,paint,6)
    tube('Trunk_gap',[(side*x,skin_h(x,z)+.002,warp(side*x,z)) for x,z in [( .65,-1.76),(.67,-1.90),(.665,-2.08),(.62,-2.23)]],.0025,seammat,5)
tube('Trunk_lip',[(x,skin_h(x,-2.29)+.005,warp(x,-2.29)) for x in [-.72+i*1.44/40 for i in range(41)]],.009,paint,6)

# Front and rear detailing use curved patch geometry, not texture stickers.
def fascia_z(x,h,front=True,offset=.006):
    return end_z(x,h,front)+(offset if front else -offset)
def patch(name,coords,mat,front=True,offset=.009):
    # Convex polygon with an actual curved center and subdivided triangle fan.
    center=(sum(p[0] for p in coords)/len(coords),sum(p[1] for p in coords)/len(coords))
    edge=[]
    for a,b in zip(coords,coords[1:]+coords[:1]):
        for j in range(8):edge.append((a[0]+(b[0]-a[0])*j/8,a[1]+(b[1]-a[1])*j/8))
    verts=[(x,h,fascia_z(x,h,front,offset)) for x,h in [center]+edge]
    obj=mesh(name,verts,[(0,i+1,(i+1)%len(edge)+1) for i in range(len(edge))],mat)
    return obj
def fascia_line(name,coords,mat,r=.006,front=True,offset=.014,closed=False):
    points=[]
    pairs=list(zip(coords,coords[1:]+coords[:1])) if closed else list(zip(coords,coords[1:]))
    for a,b in pairs:
        for j in range(5):
            t=j/5;x=a[0]+(b[0]-a[0])*t;h=a[1]+(b[1]-a[1])*t
            points.append((x,h,fascia_z(x,h,front,offset)))
    if not closed:
        x,h=coords[-1];points.append((x,h,fascia_z(x,h,front,offset)))
    return tube(name,points,r,mat,6,closed)

grillepoly=[(-.45,.893),(.45,.893),(.475,.839),(.403,.596),(.32,.566),(-.32,.566),(-.403,.596),(-.475,.839)]
patch('Grille',grillepoly,black)
fascia_line('Grille_surround',grillepoly,darkmetal,.009,closed=True)
fascia_line('Grille_top_blade',[(-.427,.896),(.427,.896)],chrome,.003)
for i,h in enumerate([.608,.661,.714,.767,.820,.866]):
    half=.35+i*.014
    fascia_line('Grille_fin',[(-half,h),(half,h)],darkmetal,.008)
    fascia_line('Grille_fin_edge',[(-half,h+.004),(half,h+.004)],chrome,.0022,offset=.023)
for x in [-.3,-.15,0,.15,.3]:fascia_line('Grille_crossbar',[(x,.585),(x,.88)],black,.005)
patch('Lower_intake',[(-.57,.424),(.57,.424),(.54,.316),(-.54,.316)],black)
for h in [.339,.365,.391]:fascia_line('Lower_intake_fin',[(-.525,h),(.525,h)],darkmetal,.004)
for side in [-1,1]:
    poly=[(side*.496,.897),(side*.712,.914),(side*.867,.839),(side*.854,.724),(side*.675,.730),(side*.539,.774)]
    lamp=empty('Headlight_L' if side==1 else 'Headlight_R')
    parent(patch('Headlight_housing',poly,black,offset=.012),lamp)
    parent(patch('Headlight_cover',poly,clear,offset=.017),lamp)
    parent(fascia_line('LED_signature',[(side*.52,.88),(side*.70,.895),(side*.844,.829),(side*.833,.748)],frontled,.0065,offset=.028),lamp)
    parent(fascia_line('LED_lower',[(side*.559,.784),(side*.676,.749),(side*.81,.746)],frontled,.004,offset=.028),lamp)
    for x,h in [(.606,.822),(.752,.803)]:
        coords=[(side*(x+.032*math.cos(a)),h+.035*math.sin(a)) for a in [j*2*PI/20 for j in range(20)]]
        parent(fascia_line('Projector_bezel',coords,rim,.005,offset=.027,closed=True),lamp)
        parent(patch('LED_projector',[(side*(x-.015),h+.016),(side*(x+.015),h+.016),(side*(x+.015),h-.016),(side*(x-.015),h-.016)],frontled,offset=.027),lamp)
    vent=[(side*.59,.515),(side*.826,.54),(side*.824,.325),(side*.623,.30),(side*.565,.364)]
    patch('Brake_air_intake',vent,black)
    fascia_line('Air_intake_surround',vent,darkmetal,.012,closed=True)
    for x in [.64,.71,.78]:fascia_line('Air_intake_blade',[(side*x,.336),(side*(x+.015),.497)],darkmetal,.011)
    # Flush bumper sensor circles.
    for x in [side*.35,side*.78]:
        tube('Parking_sensor',[(x+.012*math.cos(a),.462+.012*math.sin(a),fascia_z(x,.462,True,.016)) for a in [i*2*PI/20 for i in range(20)]],.0018,seammat,5,True)
    rpoly=[(side*.30,.786),(side*.79,.772),(side*.79,.638),(side*.38,.664)]
    rear=empty('Taillight_L' if side==1 else 'Taillight_R')
    parent(patch('Rear_lamp_housing',rpoly,black,False,.010),rear)
    parent(patch('Rear_lamp_cover',rpoly,redlens,False,.016),rear)
    parent(fascia_line('Rear_LED_upper',[(side*.336,.757),(side*.757,.745),(side*.748,.689),(side*.402,.701)],rearled,.008,False,.022),rear)
    parent(fascia_line('Rear_LED_lower',[(side*.414,.681),(side*.721,.674)],rearled,.004,False,.023),rear)
    # Small rear reflectors and restrained metal exhaust surrounds.
    fascia_line('Rear_reflector',[(side*.58,.415),(side*.743,.415)],redlens,.008,False,.014)
    exhaust=[(side*.55,.34),(side*.75,.34),(side*.733,.286),(side*.565,.286)]
    patch('Exhaust_dark',exhaust,black,False,.027)
    fascia_line('Exhaust_trim',exhaust,darkmetal,.008,False,.03,True)
patch('Rear_diffuser',[(-.78,.369),(.78,.369),(.765,.257),(-.765,.257)],black,False,.01)
patch('Registration_recess',[(-.252,.705),(.252,.705),(.252,.527),(-.252,.527)],black,False,.016)
box('Rear_registration_plate',(0,.61,fascia_z(0,.61,False,.026)),(.433,.116,.008),darkmetal,.013)

# Wheels use radial profiles, inset brakes and individual forked alloy spokes.
def lathe_x(name,center,profile,mat,segments=64):
    cx,cy,cz=center;verts=[];faces=[]
    for axial,r in profile:
        for j in range(segments):
            a=j*2*PI/segments;verts.append((cx+axial,cy+r*math.sin(a),cz+r*math.cos(a)))
    for i in range(len(profile)-1):
        for j in range(segments):
            a=i*segments+j;b=i*segments+(j+1)%segments;faces.append((a,b,b+segments,a+segments))
    return mesh(name,verts,faces,mat)
def spoke(name,cx,cy,cz,angle,mat):
    # Forked, swept spoke with a shallow sculpted cross-section.
    pts=[(.072,-.038),(.205,-.030),(.27,-.018),(.269,.006),(.19,.008),(.075,.027)]
    verts=[]
    for x in [cx-.012,cx+.012]:
        for r,t in pts:
            y=cy+r*math.sin(angle)+t*math.cos(angle);z=cz+r*math.cos(angle)-t*math.sin(angle)
            verts.append((x,y,z))
    n=len(pts);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    o=mesh(name,verts,faces,mat)
    bpy.context.view_layer.objects.active=o;o.select_set(True)
    mod=o.modifiers.new('Spoke edge radii','BEVEL');mod.width=.005;mod.segments=2
    bpy.ops.object.modifier_apply(modifier=mod.name);o.select_set(False);return o

for side in [-1,1]:
    for label,z in [('F',1.44),('R',-1.46)]:
        suffix=label+('L' if side==1 else 'R');cx=side*.851;cy=wheel_h
        w=empty('Wheel_'+suffix,(cx,cy,z))
        # Rounded tire shoulders and recessed bead, visibly distinct from the rim.
        tireprofile=[(-.122,.278),(-.127,.316),(-.115,.348),(-.093,.366),(-.070,.371),(.070,.371),(.093,.366),(.115,.348),(.127,.316),(.122,.278)]
        parent(lathe_x('Tire_'+suffix,(cx,cy,z),tireprofile,rubber,64),w)
        outer=side*.124
        parent(lathe_x('Rim_'+suffix,(cx,cy,z),[(side*.125,.263),(side*.128,.276),(side*.12,.287),(side*.083,.292),(-side*.108,.286),(-side*.108,.263),(side*.125,.263)],rim,64),w)
        # Thin polished perimeter and concentric tire sidewall embossing.
        for rad,mat,thick,ax in [(.283,chrome,.0045,side*.127),(.328,rubber,.0018,side*.124),(.35,rubber,.0018,side*.113)]:
            parent(tube('Wheel_ring',[(cx+ax,cy+rad*math.sin(a),z+rad*math.cos(a)) for a in [i*2*PI/64 for i in range(64)]],thick,mat,6,True),w)
        # Four circumferential grooves, shallow and dark: no expensive normal map.
        for ax in [-.052,0,.052]:
            parent(tube('Tread_groove',[(cx+ax,cy+.3714*math.sin(a),z+.3714*math.cos(a)) for a in [i*2*PI/48 for i in range(48)]],.002,seammat,4,True),w)
        parent(lathe_x('Brake_rotor',(cx,cy,z),[(side*.051,.075),(side*.051,.234),(side*.061,.234),(side*.061,.075)],brake,64),w)
        parent(lathe_x('Wheel_hub',(cx,cy,z),[(side*.08,.0),(side*.08,.069),(side*.138,.069),(side*.142,.054),(side*.142,0)],darkmetal,40),w)
        for k in range(10):
            a=k*2*PI/10
            parent(spoke('Alloy_spoke',cx+side*.113,cy,z,a,rim),w)
        for k in range(5):
            a=k*2*PI/5+.3
            parent(ellipsoid('Wheel_bolt',(cx+side*.147,cy+.042*math.sin(a),z+.042*math.cos(a)),(.006,.008,.008),chrome,8,4),w)
        parent(box('Brake_caliper',(cx+side*.069,cy+.02,z-.193),(.066,.165,.071),caliper,.016),w)

# A restrained interior gives the tinted glass depth without costly upholstery.
box('Cabin_floor',(0,.72,-.19),(1.45,.07,2.6),interior,.04)
box('Dashboard',(0,.94,.81),(1.57,.17,.38),interior,.055)
box('Rear_shelf',(0,1.00,-1.40),(1.48,.08,.37),interior,.045)
for x in [-.405,.405]:
    for z in [.01,-.94]:
        box('Seat_cushion',(x,.76,z),(.48,.14,.48),interior,.065)
        back=box('Seat_back',(x,.985,z-.185),(.47,.47,.13),interior,.057);back.rotation_euler.x=-.12
        box('Headrest',(x,1.246 if z>-.5 else 1.125,z-.225),(.235,.17,.106),interior,.037)
tube('Steering_wheel',[(.425+.154*math.cos(a),1.00+.154*math.sin(a),.617-.055*math.sin(a)) for a in [i*2*PI/40 for i in range(40)]],.016,interior,8,True)
box('Center_console',(0,.828,.08),(.23,.15,.78),interior,.045)

# Join small meshes by material within each named pivot, retaining the runtime API.
bpy.ops.object.select_all(action='DESELECT')
protected={'Roof','Glass','Grille'}
for p in [None]+[o for o in car.objects if o.type=='EMPTY']:
    groups={}
    for o in list(car.objects):
        if o.type=='MESH' and o.parent==p and o.name not in protected:
            key=o.data.materials[0].name
            groups.setdefault(key,[]).append(o)
    for matname,objects in groups.items():
        if len(objects)<2:continue
        # Keep Tire_XX and Rim_XX as the names of their merged material groups.
        active=next((o for o in objects if o.name=='Body' or o.name.startswith(('Tire_','Rim_'))),objects[0])
        for o in objects:o.select_set(True)
        bpy.context.view_layer.objects.active=active;bpy.ops.object.join()
        bpy.ops.object.select_all(action='DESELECT')

# Weld the actual shell boundaries so adjoining rounded panels share normals.
import bmesh
bm=bmesh.new();bm.from_mesh(body.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00005)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(body.data);bm.free();body.data.update()

for o in car.objects:
    if o.type=='MESH':
        o.data.validate();o.data.update()
        # Recalculate bounds/normals before export; keep custom bevel normals.
        o['asset_authoring']='Original procedural geometry for Legion Auto Rent'

# Model-only source and export: no lights/floor/camera accidentally shipped in GLB.
bpy.context.scene.unit_settings.system='METRIC'
for o in car.objects:o.select_set(True)
bpy.context.view_layer.objects.active=body
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'legion-sedan.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'legion-sedan.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True,export_animations=False,export_cameras=False,export_lights=False,export_extras=False)
triangles=sum(len(p.vertices)-2 for o in car.objects if o.type=='MESH' for p in o.data.polygons)
report={'blender':bpy.app.version_string,'meshes':sum(o.type=='MESH' for o in car.objects),'triangles_before_export':triangles,'materials':len(bpy.data.materials),'source':'tools/build_hero_sedan.py','output':'assets/hero-sedan/legion-sedan.glb'}
(OUT/'build.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report),flush=True)
