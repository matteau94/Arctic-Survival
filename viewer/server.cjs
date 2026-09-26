const http=require('http'),fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..');
const types={'.html':'text/html','.js':'text/javascript','.json':'application/json','.glb':'model/gltf-binary','.bin':'application/octet-stream','.css':'text/css'};
http.createServer((req,res)=>{
  let url;
  try {url=decodeURIComponent(new URL(req.url,'http://localhost').pathname);} catch {res.writeHead(400).end();return;}
  if(url==='/')url='/viewer/index.html';
  const file=path.resolve(root,'.'+url);
  const allowed=url.startsWith('/viewer/') || Object.keys({'/Penguin_Animated.glb':1,'/ArcticFox_Animated.glb':1,'/Orca_Animated.glb':1,'/Fish Animated.glb':1,'/Polar Bear Animated.glb':1,'/Scenery/Winter Cabin.glb':1,'/Scenery/Snowy Village.glb':1}).includes(url);
  if(!allowed||!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
  fs.stat(file,(err,stat)=>{
    if(err||!stat.isFile()){res.writeHead(404).end('Not found');return;}
    res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Content-Length':stat.size,'Cache-Control':'no-cache'});
    if(req.method==='HEAD')res.end();else fs.createReadStream(file).pipe(res);
  });
}).listen(8765,'127.0.0.1',()=>console.log('Arctic viewer: http://127.0.0.1:8765'));
