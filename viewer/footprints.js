import * as THREE from 'three';
import { createSnowImpressions } from './snow-impressions.js';

// Contact comes from animated outsole samples, never from a movement/clip name.
export function createFootprints(scene, surface, player, terrainMeshes=[]) {
  const snow=createSnowImpressions(THREE,scene,surface,terrainMeshes);
  const point=new THREE.Vector3();
  const contacts=(player.soleSamples||[]).map(sample=>({sample,touching:false,last:new THREE.Vector3(Infinity,Infinity,Infinity)}));
  return function updateFootprints(){
    let currentMesh=null;
    for(const contact of contacts){
      const sample=contact.sample;
      if(currentMesh!==sample.mesh){sample.mesh.skeleton.update();currentMesh=sample.mesh;}
      sample.mesh.getVertexPosition(sample.index,point).applyMatrix4(sample.mesh.matrixWorld);
      const height=surface.height(point.x,point.z);
      const touching=height!==null&&point.y-height<=.012&&point.y-height>=-.05;
      if(touching&&(!contact.touching||point.distanceToSquared(contact.last)>.025**2)){
        snow.stamp(point.x,point.z,.055,.025);
        contact.last.copy(point);
      }
      contact.touching=touching;
    }
    snow.update(player.root.position);
  };
}
