import * as THREE from 'three';
import { animate } from './gameplay.js';

// Visible posed geometry only: hidden helpers and empty AABB corners are not
// animal footprint. The radius remains conservative for any indoor yaw.
export function visibleAnimalFootprint(a){
  a.root.updateMatrixWorld(true);
  const box=new THREE.Box3(),vertex=new THREE.Vector3(),p=a.root.position;
  let radius=0;
  // root.visible is distance culling, not model visibility. Still measure a
  // culled neighbor while respecting hidden helpers within its model.
  for(const model of a.root.children)model.traverseVisible(mesh=>{
    if(!mesh.isMesh||!mesh.geometry.attributes.position)return;
    if(mesh.isSkinnedMesh)mesh.skeleton.update();
    for(let i=0;i<mesh.geometry.attributes.position.count;i++){
      mesh.getVertexPosition(i,vertex).applyMatrix4(mesh.matrixWorld);
      box.expandByPoint(vertex);radius=Math.max(radius,Math.hypot(vertex.x-p.x,vertex.z-p.z));
    }
  });
  return {box,radius:box.isEmpty()?Infinity:radius};
}

/** At most three borrowed actors. The wildlife streamer retains ownership. */
export function createCompanionRoom({world,player,getCompanions,canSee,getBags,findReturn}){
  const residents=new Map(),next=new THREE.Vector3();
  const notice=document.createElement('div');notice.className='camping-hint';notice.hidden=true;notice.setAttribute('role','status');document.body.append(notice);
  let noticeTime=0;
  let room=null,tentIndex=null,bags=[];
  const distance=(a,b)=>Math.hypot(a.x-b.x,a.z-b.z);
  function clear(p,radius,except=null){
    if(Math.abs(p.x)+radius>3.35||Math.abs(p.z)+radius>3.85)return false;
    if(Math.abs(p.x)<1.5+radius&&p.z+radius>1.9)return false;
    if(distance(p,player.root.position)<radius+.45)return false;
    for(const box of bags)if(p.x+radius>box.min.x&&p.x-radius<box.max.x&&p.z+radius>box.min.z&&p.z-radius<box.max.z)return false;
    for(const [a,r] of residents)if(a!==except&&distance(p,a.root.position)<radius+r.radius+.15)return false;
    return true;
  }
  function leave(){
    for(const [a,r] of residents){
      world.add(a.root);a.root.position.copy(r.outside);a.root.quaternion.copy(r.rotation);
      a.companionRoom=null;a.home.copy(r.outside);a.destination.copy(r.outside);a.origin.copy(r.outside);
      a.think=0;a.animationElapsed=0;a.root.visible=true;animate(a,'idle');a.root.updateMatrixWorld(true);
    }
    residents.clear();room=null;tentIndex=null;bags=[];notice.hidden=true;noticeTime=0;
  }
  return {
    leave,
    worldPosition:a=>residents.get(a)?.outside??a.root.position,
    sameSpace:a=>a.root.parent===player.root.parent,
    blocksPlayer(x,z){for(const [a,r] of residents)if(Math.hypot(x-a.root.position.x,z-a.root.position.z)<r.radius+.4)return true;return false;},
    overlaps(bounds){for(const [a,r] of residents){const p=a.root.position;if(p.x+r.radius>bounds.min.x&&p.x-r.radius<bounds.max.x&&p.z+r.radius>bounds.min.z&&p.z-r.radius<bounds.max.z)return true;}return false;},
    // Keep outdoor AI out of the reserved return footprints during spectating.
    blocksOutdoor(x,z,actor){for(const r of residents.values())if(Math.hypot(x-r.outside.x,z-r.outside.z)<r.radius+(actor.renderRadius||1))return true;return false;},
    enter(destination,index,outsidePlayer){
      room=destination;tentIndex=index;bags=getBags(index);
      const reasons=new Set();
      // Poses stay fixed during this synchronous transfer. Share measurements
      // across admissions, then discard them before the next entry.
      const footprints=new Map();
      const footprint=a=>{
        if(!footprints.has(a))footprints.set(a,visibleAnimalFootprint(a));
        return footprints.get(a);
      };
      const companions=getCompanions();
      if(companions.some(({a})=>a.root.parent===world)&&!companions.some(({a,r})=>
        r.mode==='follow'&&a.root.parent===world&&a.root.position.distanceTo(outsidePlayer)<=4)){
        reasons.add('Set your companion to Follow and bring it within 4 m before entering.');
      }
      for(const {a,r} of companions){
        if(residents.size>=3)break;
        if(r.mode!=='follow'||a.root.parent!==world||a.root.position.distanceTo(outsidePlayer)>4)continue;
        if(!canSee(outsidePlayer,a.root.position)){reasons.add('Move your companion to the open doorway.');continue;}
        // Admission only (at most three): measure posed, visible vertices.
        // setFromObject includes hidden Icosphere helpers; AABB corners also
        // overestimate the radius of a long animal standing diagonally.
        const {box,radius:posedRadius}=footprint(a),p=a.root.position;
        // Stationary idle only indoors: reserve 25% plus 20 cm for pose motion.
        const radius=posedRadius*1.25+.2;
        if(box.isEmpty()||!Number.isFinite(radius)||radius>1.2||box.max.y-box.min.y+.25>3.5){reasons.add('Your companion needs more room than this tent allows.');continue;}
        const outside=findReturn(a,radius,outsidePlayer,index,footprint);
        if(!outside){reasons.add('Your companion needs clear, level ground outside to return safely.');continue;}
        let slot=null;
        for(let z=.8;z>=-3.2&&!slot;z-=.5)for(let x=-2.7;x<=2.7;x+=.5){
          next.set(x,p.y-box.min.y+.02,z);if(clear(next,radius)){slot=next.clone();break;}
        }
        if(!slot){reasons.add('No clear tent floor for your companion; sleeping bags and the doorway need space.');continue;}
        residents.set(a,{outside,rotation:a.root.quaternion.clone(),radius,r});
        // Stream records always contain outdoor coordinates, even during reparenting.
        r.data={...r.data,position:outside.toArray(),rotation:a.root.rotation.y};
        a.companionRoom=room;room.add(a.root);a.root.position.copy(slot);a.root.rotation.set(0,0,0);
        a.animationElapsed=0;a.root.visible=true;animate(a,'idle');a.root.updateMatrixWorld(true);
      }
      notice.textContent=[...reasons].join(' ');notice.hidden=!reasons.size;noticeTime=reasons.size?8:0;
    },
    update(dt,running){
      if(!room||!running)return;
      if(noticeTime>0){noticeTime=Math.max(0,noticeTime-dt);notice.hidden=noticeTime===0;}
      for(const [a,entry] of residents){
        // Keep the admitted slot; G changes the mode used on exit.
        a.state=a.petting?'Waiting for pet':entry.r.mode==='follow'?'Waiting indoors (Follow)':'Staying indoors';
        animate(a,'idle');a.mixer.update(dt);a.root.updateMatrixWorld(true);
      }
    },
  };
}
