import * as THREE from 'three';
import { animate } from './gameplay.js';

const smooth=t=>{t=THREE.MathUtils.clamp(t,0,1);return t*t*(3-2*t);};
const normalized=name=>String(name??'').replace(/[._]/g,'').toLowerCase();
const CONTACT_ERROR=.045,JOINT_LIMITS=[1.05,1.4],PASSES=8;
function bone(root,name){
  let found=null;
  root.traverse(node=>{if(node.isBone&&(normalized(node.userData?.name)===normalized(name)||normalized(node.name)===normalized(name)))found=node;});
  return found;
}

/** Additive runtime pose, evaluated AFTER the owner's single mixer update. */
export function createAnimalPetting({getPlayer,allowed,canSee,onStart=()=>{}}){
  let session=null;
  const pivot=new THREE.Vector3(),handPoint=new THREE.Vector3(),target=new THREE.Vector3();
  const from=new THREE.Vector3(),to=new THREE.Vector3(),parentQ=new THREE.Quaternion(),delta=new THREE.Quaternion();
  const identity=new THREE.Quaternion();
  const surfacePoint=new THREE.Vector3(),strokePoint=new THREE.Vector3();
  function contacts(s){
    s.animal.root.updateMatrixWorld(true);s.head.getWorldPosition(target);
    target.y+=s.animal.type==='penguin'?.1:.07;
    const samples=[-.055,0,.055].map(offset=>({aim:target.clone().add(new THREE.Vector3(Math.sin(s.animal.root.rotation.y)*offset,0,Math.cos(s.animal.root.rotation.y)*offset)),distance:Infinity}));
    let meshes=0;
    s.animal.root.traverseVisible(mesh=>{
      if(!mesh.isMesh||meshes++>=4||!mesh.geometry.attributes.position)return;
      if(mesh.isSkinnedMesh)mesh.skeleton.update();
      const count=mesh.geometry.attributes.position.count,stride=Math.max(1,Math.ceil(count/4096));
      for(let i=0;i<count;i+=stride){
        mesh.getVertexPosition(i,surfacePoint).applyMatrix4(mesh.matrixWorld);
        for(const sample of samples){const distance=sample.aim.distanceToSquared(surfacePoint);if(distance<sample.distance){sample.distance=distance;sample.mesh=mesh;sample.index=i;}}
      }
    });
    return samples.every(sample=>sample.mesh&&sample.distance<.2*.2)?samples:null;
  }
  function restore(s=session){
    if(!s)return;
    for(const entry of s.pose){entry.bone.position.copy(entry.position);entry.bone.quaternion.copy(entry.quaternion);entry.bone.scale.copy(entry.scale);}
    s.pose.length=0;
  }
  function contact(s,stroke){
    const center=s.contacts[1],edge=s.contacts[stroke<0?0:2];
    for(const sample of [center,edge])if(sample.mesh.isSkinnedMesh)sample.mesh.skeleton.update();
    center.mesh.getVertexPosition(center.index,target).applyMatrix4(center.mesh.matrixWorld);
    edge.mesh.getVertexPosition(edge.index,strokePoint).applyMatrix4(edge.mesh.matrixWorld);
    target.lerp(strokePoint,Math.min(1,Math.abs(stroke)/.055));
  }
  function solve(s){
    for(const joint of s.joints)s.pose.push({bone:joint,position:joint.position.clone(),quaternion:joint.quaternion.clone(),scale:joint.scale.clone()});
    for(let pass=0;pass<PASSES;pass++)for(let i=0;i<s.joints.length;i++){
      const joint=s.joints[i],base=s.pose[i].quaternion;
      joint.getWorldPosition(pivot);s.hand.getWorldPosition(handPoint);
      joint.parent.getWorldQuaternion(parentQ).invert();
      from.copy(handPoint).sub(pivot).applyQuaternion(parentQ).normalize();
      to.copy(target).sub(pivot).applyQuaternion(parentQ).normalize();
      if(from.lengthSq()<.5||to.lengthSq()<.5)continue;
      delta.setFromUnitVectors(from,to);
      // Limit both each correction and the total deviation from authored pose.
      const step=identity.angleTo(delta);if(step>.25)delta.slerp(identity,1-.25/step);
      joint.quaternion.premultiply(delta);
      const angle=base.angleTo(joint.quaternion);
      if(angle>JOINT_LIMITS[i])joint.quaternion.slerp(base,1-JOINT_LIMITS[i]/angle);
      joint.updateWorldMatrix(false,true);
    }
    s.hand.getWorldPosition(handPoint);
    return handPoint.distanceTo(target)<=CONTACT_ERROR;
  }
  function reachable(s,yaw){
    // Sample existing crouch tracks without advancing or disturbing the mixer.
    // Every temporary property and root rotation is restored even on rejection.
    const saved=[],rotation=s.player.root.quaternion.clone();
    try{
      s.player.root.rotation.y=yaw;
      for(const track of s.player.animationClips.crouchIdle.tracks){
        const match=/^(.+)\.(position|quaternion|scale)$/.exec(track.name);
        if(!match)return false;
        const node=s.player.root.getObjectByName(match[1]);if(!node)return false;
        const property=match[2];saved.push({node,property,value:node[property].clone()});
        node[property].fromArray(track.createInterpolant().evaluate(.75));
      }
      s.player.root.updateMatrixWorld(true);s.animal.root.updateMatrixWorld(true);
      for(const stroke of [0,-.055,.055]){
        contact(s,stroke);const reached=solve(s);restore(s);s.player.root.updateMatrixWorld(true);
        if(!reached)return false;
      }
      return true;
    }finally{
      restore(s);for(const {node,property,value} of saved)node[property].copy(value);
      s.player.root.quaternion.copy(rotation);s.player.root.updateMatrixWorld(true);
    }
  }
  function cancel(){
    if(!session)return;
    restore();const {player,animal}=session;session=null;
    player.petting=false;animal.petting=false;
    animate(player,'idle');player.state='Idle';player.root.updateMatrixWorld(true);
  }
  function valid(){
    if(!session)return false;
    const {player,animal}=session;
    return allowed()&&player.root.parent===animal.root.parent&&
      player.root.position.distanceTo(animal.root.position)<1.6&&canSee(player.root.position,animal.root.position);
  }
  return {
    active:()=>!!session,cancel,
    start(animal){
      if(session||!allowed())return false;
      const player=getPlayer();
      if(player.root.parent!==animal.root.parent||player.root.position.distanceTo(animal.root.position)>1.35||!canSee(player.root.position,animal.root.position))return false;
      const hand=bone(player.root,'hand.R'),elbow=bone(player.root,'forearm.R'),shoulder=bone(player.root,'upper_arm.R');
      if(!hand||!elbow||!shoulder||!player.animationClips.crouchIdle)return false;
      const candidate={player,animal,hand:bone(player.root,'prop.R')??hand,joints:[elbow,shoulder],head:bone(animal.root,'head'),time:0,pose:[]};
      const facing=Math.atan2(animal.root.position.x-player.root.position.x,animal.root.position.z-player.root.position.z);
      if(!candidate.head)return false;
      candidate.contacts=contacts(candidate);
      if(!candidate.contacts||!reachable(candidate,facing))return false;
      session=candidate;
      player.petting=true;animal.petting=true;onStart();
      player.root.rotation.y=facing;
      player.turnStepTime=0;animate(player,'crouchIdle');animate(animal,'idle');
      return true;
    },
    beforeFrame(){restore();if(session&&!valid())cancel();},
    tick(dt){
      if(!session)return;
      if(!valid()){cancel();return;}
      const s=session;s.time+=dt;if(s.time>=2.4){cancel();return;}
      const weight=smooth((s.time-.2)/.5)*smooth((2.4-s.time)/.4);
      s.player.root.updateMatrixWorld(true);s.animal.root.updateMatrixWorld(true);
      // Don't stroke during approach/retraction. Reject a lost contact after crouching.
      contact(s,weight===1?.055*Math.sin(s.time*11):0);
      const reached=solve(s);
      if(!reached&&s.time>=.7){cancel();return;}
      for(const entry of s.pose){
        // Preserve the solved value: slerpQuaternions cannot alias its target.
        delta.copy(entry.bone.quaternion);entry.bone.quaternion.copy(entry.quaternion).slerp(delta,weight);
      }
      s.player.root.updateMatrixWorld(true);
      s.hand.getWorldPosition(handPoint);
      const touching=weight===1&&handPoint.distanceTo(target)<=CONTACT_ERROR;
      s.player.state=touching?'Petting':'Reaching';s.animal.state=touching?'Being petted':'Waiting';
    },
  };
}
