import * as THREE from 'three';

/** One reusable runtime ration; ownership stays in the backpack. */
export function createHeldFood({inventory,getPlayer,canHold}){
  let prop=null;
  const heldId=()=>inventory.heldId();
  function stow(){if(prop)prop.visible=false;return inventory.putAway();}
  inventory.subscribe(state=>{if(prop&&state.heldId!=='food')prop.visible=false;});
  function attachment(){
    const root=getPlayer()?.root;
    let socket=null,hand=null;
    root?.traverse(node=>{
      if(!node.isBone)return;
      // Prefer original GLTF metadata; the loader strips dots at runtime.
      if(node.userData?.name==='prop.R'||/^prop[._]?R$/.test(node.name))socket=node;
      if(node.userData?.name==='hand.R'||/^hand[._]?R$/.test(node.name))hand=node;
    });
    return {socket,hand};
  }
  return {
    heldId,
    stow,
    toggle(id){
      if(id===heldId())return stow();
      const item=inventory.snapshot().items.find(item=>item.id===id&&item.quantity>0);
      if(id!=='food'||item?.category!=='food')return {ok:false,message:'You must own trail food to hold it.'};
      if(!canHold())return {ok:false,message:'Food cannot be held here right now.'};
      const {socket,hand}=attachment();
      if(!socket&&!hand)return {ok:false,message:'The character has no available hand attachment.'};
      if(!prop){
        prop=new THREE.Group();prop.name='HeldTrailFood';
        const wrapper=new THREE.Mesh(new THREE.BoxGeometry(.075,.15,.035),new THREE.MeshStandardMaterial({color:0xc58b46,roughness:.9}));
        const band=new THREE.Mesh(new THREE.BoxGeometry(.078,.045,.038),new THREE.MeshStandardMaterial({color:0xf0e4bd,roughness:.9}));
        prop.add(wrapper,band);
        // The authored grip socket is 7 cm along the hand, 3.5 cm into the palm.
        if(!socket){prop.position.set(0,.07,.035);prop.rotation.z=Math.PI/2;}
        (socket||hand).add(prop);
      }
      const result=inventory.hold(id);prop.visible=result.ok;
      // The scene disables automatic world updates, including while paused.
      prop.updateWorldMatrix(true,true);
      return result;
    },
    update({stow:shouldStow=false,hidden=false}={}){
      if(shouldStow)stow();
      if(!prop)return;
      prop.visible=heldId()==='food'&&!hidden;
      if(prop.visible)prop.updateWorldMatrix(true,true);
    },
  };
}
