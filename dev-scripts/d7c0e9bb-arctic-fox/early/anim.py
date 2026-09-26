import bpy, math
from mathutils import Vector, Quaternion, Matrix
rig=bpy.data.objects["FoxRig"]; arm=rig.data
R=math.radians
X=Vector((1,0,0)); Y=Vector((0,1,0)); Z=Vector((0,0,1))
def qx(a): return Quaternion(X,a)
def qy(a): return Quaternion(Y,a)
def qz(a): return Quaternion(Z,a)
def mj(w): return w*w*w*(10-15*w+6*w*w)
def sst(e0,e1,x):
    t=min(1,max(0,(x-e0)/(e1-e0))); return t*t*(3-2*t)
def periodic_curve(pts):
    pts=sorted(pts)
    def f(u):
        u%=1.0; n=len(pts)
        for i in range(n):
            u0,v0=pts[i]; u1,v1=pts[(i+1)%n]
            if i==n-1: u1+=1
            uu=u if u>=u0 else u+1
            if u0<=uu<u1 or (i==n-1):
                if not (u0<=uu<=u1): continue
                um,vm=pts[i-1]; um=um-1 if i-1<0 else um
                u2,v2=pts[(i+2)%n]
                if i+2>=n: u2+=1
                t=(uu-u0)/(u1-u0)
                m0=(v1-vm)/(u1-um)*(u1-u0); m1=(v2-v0)/(u2-u0)*(u1-u0)
                h00=2*t**3-3*t*t+1; h10=t**3-2*t*t+t; h01=-2*t**3+3*t*t; h11=t**3-t*t
                return h00*v0+h10*m0+h01*v1+h11*m1
        return pts[0][1]
    return f
def vdir(a):  # joint -> distal, a>0 means distal end ahead (toward -Y)
    return Vector((0,-math.sin(a),-math.cos(a)))
def ik2(A,T,a,b,pole):
    d=(T-A); L=d.length; L=min(max(L,abs(a-b)+1e-4),a+b-1e-4); u=d.normalized()
    ca=(a*a+L*L-b*b)/(2*a*L); sa=math.sqrt(max(0,1-ca*ca))
    n=pole-u*pole.dot(u); n.normalize()
    J=A+u*a*ca+n*a*sa; Tn=A+u*L
    return J,Tn,(T-A).length/(a+b)
bones=list(arm.bones)
order=[]; seen=set()
def visit(b):
    if b.name in seen: return
    if b.parent: visit(b.parent)
    seen.add(b.name); order.append(b)
for b in bones: visit(b)
BL={b.name:b for b in bones}
def rest_dir(n): b=BL[n]; return (b.tail_local-b.head_local).normalized()
LEN={b.name:b.length for b in bones}
ball0={s:BL[f'hock.{s}'].tail_local.copy() for s in 'LR'}
fball0={s:BL[f'hand.{s}'].tail_local.copy() for s in 'LR'}
def ang_of(v): return math.atan2(-v.y,-v.z)
PSI_REST=sum(ang_of(rest_dir(f'hand.{s}')) for s in 'LR')/2
PHI_REST=sum(ang_of(rest_dir(f'hock.{s}')) for s in 'LR')/2
TOE_F=sum(ang_of(rest_dir(f'toes_front.{s}')) for s in 'LR')/2
TOE_H=sum(ang_of(rest_dir(f'toes_hind.{s}')) for s in 'LR')/2
TAIL_REST=[math.atan2(-(BL[f'tail{k}'].tail_local-BL[f'tail{k}'].head_local).z,(BL[f'tail{k}'].tail_local-BL[f'tail{k}'].head_local).y) for k in range(1,7)]  # downward slope
def leg_state(u,d,S,y0,h,x,zr,front):
    u%=1.0
    if u<d:
        s=u/d; y=y0-S/2+S*s; z=zr; load=math.sin(math.pi*s); sw=None
    else:
        w=(u-d)/(1-d); y=y0+S/2-S*mj(w)
        # small reach overshoot then settle just before touchdown
        y-=S*0.06*math.sin(math.pi*sst(0.55,1.0,w))
        z=zr+h*math.sin(math.pi*(w**0.85))**1.3; load=0.0; sw=w
    return Vector((x,y,z)),load,sw
def run(G):
    N=G['frames']; name=G['name']
    act=bpy.data.actions.get(name)
    if act: bpy.data.actions.remove(act)
    act=bpy.data.actions.new(name); act.use_fake_user=True
    rig.animation_data_create(); rig.animation_data.action=act
    for pb in rig.pose.bones: pb.rotation_mode='QUATERNION'; pb.matrix_basis=Matrix()
    psi=periodic_curve(G['psi']); phi=periodic_curve(G['phi'])
    # mean loads for zero-mean vertical motion
    def loads_at(t):
        out={}
        for leg in ('LF','RF','LH','RH'):
            p=G['legs'][leg]; front=leg[1]=='F'
            _,ld,_=leg_state(t+p,G['duty'],G['S'],0,0,0,0,front); out[leg]=ld
        return out
    samples=[loads_at(i/200) for i in range(200)]
    mean_tot=sum(sum(s.values()) for s in samples)/200
    mean_fh=sum((s['LF']+s['RF'])-(s['LH']+s['RH']) for s in samples)/200
    prevq={}; worst=0
    for f in range(N+1):
        t=f/N; ld=loads_at(t); T2=2*math.pi*t
        tot=sum(ld.values())-mean_tot
        fh=(ld['LF']+ld['RF'])-(ld['LH']+ld['RH'])-mean_fh
        lr_h=ld['LH']-ld['RH']; lr_f=ld['LF']-ld['RF']
        extra=G.get('extra',lambda t:{})(t)
        zoff=G['crouch']-G['bob']*tot+extra.get('z',0)
        xoff=G.get('sway',0)*(lr_h+lr_f)*0.5
        pitch=G['pitch']*fh+extra.get('pitch',0)
        F=extra.get('flex',0)
        # foot positions + fore/aft for yaw
        feet={}; sw={}
        for leg in ('LF','RF','LH','RH'):
            s=leg[0]; front=leg[1]=='F'
            base=(fball0 if front else ball0)[s]
            y0=G['y0f'] if front else G['y0h']
            x=math.copysign(G['xf' if front else 'xh'],base.x)
            p,_,w=leg_state(t+G['legs'][leg],G['duty'],G['S'],y0,G['hf' if front else 'hh'],x,base.z,front)
            feet[leg]=p; sw[leg]=w
        yaw_h=-G['yaw']*(feet['RH'].y-feet['LH'].y)/G['S']
        yaw_c=-G['yaw']*(feet['RF'].y-feet['LF'].y)/G['S']
        roll_h=-G['roll']*lr_h; roll_c=-G['roll']*lr_f
        Q={}; M={}
        Q['root']=Quaternion()
        Q['hips']=qz(yaw_h)@qy(roll_h)@qx(pitch-0.6*F)
        Qc=qz(yaw_c*0.6)@qy(roll_c)@qx(pitch+0.7*F)
        Q['chest']=Qc
        Q['spine1']=Q['hips'].slerp(Qc,0.33)@qx(-0.1*F); Q['spine1']=qx(0)@Q['spine1']
        Q['spine2']=Q['hips'].slerp(Qc,0.66)@qx(0.3*F)
        nk=G['neck']; hd=G['head']; nod=G.get('nod',0)*(ld['LF']+ld['RF']-0.5*(ld['LH']+ld['RH']))+extra.get('nod',0)
        Q['neck1']=qz(yaw_c*0.3)@qx(nk[0]+nod*0.5)
        Q['neck2']=qz(yaw_c*0.1)@qx(nk[1]+nod)
        Q['head']=qx(hd+nod*0.3+extra.get('head',0))          # world-stabilised gaze
        ea=G['ears']+extra.get('ears',0)
        Q['ear.L']=Q['head']@qx(-ea); Q['ear.R']=Q['head']@qx(-ea)
        # tail: carriage + lagged vertical bounce + lateral sway, amplitude grows toward the tip
        tgt=G['tail']
        for k in range(6):
            kk=k/5
            lift=TAIL_REST[k]-R(tgt[k])
            bounce=G['tbounce']*(0.3+kk)*math.sin(2*T2*G.get('tfreqv',1)-G['tlag']*(k+1)+G.get('tph',0))
            swayt=G['tsway']*(0.2+kk)*math.sin(T2-G['tlag']*(k+1)*0.6)
            Q[f'tail{k+1}']=Q['hips']@qz(swayt)@qx(lift+bounce)
        for s in 'LR':
            # scapula swings with the forelimb (big share of forelimb reach in small canids)
            fy=feet[s+'F'].y-G['y0f']
            Q[f'scapula.{s}']=Quaternion(Qc@X, G['scap']*fy/(G['S']/2))@Qc
        # --- FK pass with IK for legs
        for b in order:
            n=b.name
            if b.parent:
                p=b.parent; head=(M[p.name]@p.matrix_local.inverted()@b.matrix_local).translation
            else: head=b.matrix_local.translation.copy()
            if n=='hips': head=head+Vector((xoff,0,zoff))
            if n.startswith('thigh.') or n.startswith('upperarm.'):
                s=n[-1]; front=n.startswith('upper')
                leg=s+('
