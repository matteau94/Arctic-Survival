import * as THREE from 'three';

const smooth=t=>{t=THREE.MathUtils.clamp(t,0,1);return t*t*(3-2*t);};

// Uses the existing rig and clips. All props are small in-memory meshes.
export function startTentSetup({player,scene,surface,position,tent,onComplete,onCancel}){
  let elapsed=0,finished=false,clipName=null;
  const start=player.root.position.clone();
  const direction=new THREE.Vector3(position.x-start.x,0,position.z-start.z).normalize();
  const destination=new THREE.Vector3(position.x,0,position.z).addScaledVector(direction,-2.6);
  const savedAction=player.action,savedClip=player.clip;
  const bones={};player.root.traverse(o=>{if(o.isBone)bones[o.name]=o;});
  const rest=new Map();
  const bundle=new THREE.Mesh(new THREE.CylinderGeometry(.16,.16,.65,12),new THREE.MeshStandardMaterial({color:0xc87731,roughness:.9}));
  bundle.rotation.z=Math.PI/2;scene.add(bundle);
  const tentScale=tent.scale.clone();tent.visible=false;
  function clip(name){
    if(clipName===name)return;
    const source=player.clips.find(c=>c.name===`Human_${name}`);
    if(!source)return;
    player.action?.fadeOut(.18);
    player.action=player.mixer.clipAction(source);
    player.action.reset().setEffectiveTimeScale(1).setEffectiveWeight(1).fadeIn(.18).play();
    player.clip=source.name;clipName=name;
  }
  function restorePose(){for(const [bone,q]of rest)bone.quaternion.copy(q);rest.clear();}
  function offset(name,x,y,z){const bone=bones[name];if(!bone)return;rest.set(bone,bone.quaternion.clone());bone.quaternion.multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(x,y,z)));}
  function cleanup(){
    restorePose();scene.remove(bundle);bundle.geometry.dispose();bundle.material.dispose();
    player.action?.fadeOut(.15);
    if(savedAction)savedAction.reset().setEffectiveWeight(1).fadeIn(.15).play();
    player.action=savedAction;player.clip=savedClip;player.state='Idle';
    tent.scale.copy(tentScale);tent.updateMatrixWorld(true);
  }
  return {
    // Clear last frame's additive reach before the animation mixer evaluates.
    beforeFrame:restorePose,
    tick(dt){
      if(finished)return;
      elapsed+=dt;const t=elapsed;
      player.state='Setting up tent';
      const facing=Math.atan2(direction.x,direction.z);
      const delta=Math.atan2(Math.sin(facing-player.root.rotation.y),Math.cos(facing-player.root.rotation.y));
      player.root.rotation.y+=delta*Math.min(1,dt*8);
      let label;
      if(t<1.3){
        clip('Idle');label='Taking the tent out of your backpack';
        const reach=Math.sin(Math.PI*smooth(t/1.3));
        offset('upper_arm.R',-.8*reach,.35*reach,-.65*reach);
        offset('forearm.R',-1.35*reach,0,0);
        offset('spine_02',0,-.2*reach,0);
      }else if(t<3){
        clip('Walk');label='Carrying the packed tent';
        player.root.position.lerpVectors(start,destination,smooth((t-1.3)/1.7));
        player.root.position.y=surface.height(player.root.position.x,player.root.position.z)??start.y;
      }else if(t<4.8){clip('Gather');label='Unrolling the groundsheet';}
      else if(t<7.5){clip('Gather');label='Raising the poles and canvas';}
      else{clip('Idle');label='Finishing the tent';}
      player.root.updateMatrixWorld(true);
      if(t<3.5){
        bundle.visible=t>.45;
        const hand=bones['hand.R'];
        if(hand){hand.getWorldPosition(bundle.position);hand.getWorldQuaternion(bundle.quaternion);}
        else{bundle.position.copy(player.root.position).add(new THREE.Vector3(0,1,0));}
      }else bundle.visible=false;
      if(t>=3.5){
        tent.visible=true;
        const spread=.15+.85*smooth((t-3.5)/1.3);
        const rise=.025+.975*smooth((t-4.8)/2.7);
        tent.scale.set(tentScale.x*spread,tentScale.y*rise,tentScale.z*spread);
        tent.updateMatrixWorld(true);
      }
      bundle.updateMatrixWorld(true);
      if(t>=8.5){finished=true;cleanup();onComplete();}
      return `${label} · ${Math.min(100,Math.round(t/8.5*100))}% · Esc cancels`;
    },
    cancel(){if(finished)return;finished=true;cleanup();onCancel();},
  };
}
