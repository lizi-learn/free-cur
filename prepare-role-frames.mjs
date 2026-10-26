// Deterministic game-asset import: grid slicing, anchor alignment and a shared palette.
import sharp from 'sharp';
import {mkdir,copyFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('.',import.meta.url));
const sources=process.argv.slice(2);
if(sources.length!==3)throw Error('Expected three 4x4 generated sheets');
const out=root+'artwork/pixel-diana-v2';
const groups=[['Hand','Wait','No','IBeam'],['SizeWE','SizeNS','SizeNWSE','SizeNESW'],['Help','NWPen','SizeAll','AppStarting']];
await mkdir(out,{recursive:true});
const frames=[];
for(let sheet=0;sheet<3;sheet++){
 await copyFile(sources[sheet],out+'/source-sheet-'+sheet+'.png');
 const meta=await sharp(sources[sheet]).metadata();
 for(let row=0;row<4;row++)for(let column=0;column<4;column++){
  const left=Math.round(column*meta.width/4),top=Math.round(row*meta.height/4);
  const width=Math.round((column+1)*meta.width/4)-left,height=Math.round((row+1)*meta.height/4)-top;
  const {data}=await sharp(sources[sheet]).extract({left,top,width,height}).resize(44,44,{fit:'fill',kernel:'nearest'}).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  let minX=44,maxX=0,minY=44,maxY=0;
  for(let p=0;p<data.length;p+=4){
   // Remove generated red matte speckles, retaining the intended pink costume.
   const redMatte=data[p]>170&&data[p]>data[p+1]*2.3&&data[p]>data[p+2]*2.3;
   data[p+3]=data[p+3]>=160&&!redMatte?255:0;
   if(!data[p+3]){data.fill(0,p,p+4);continue;}
   const x=p/4%44,y=Math.floor(p/4/44);minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);
  }
  // A grid edge can contain a disconnected fragment of the neighboring row.
  // Keep the main connected sprite; contact symbols are exported separately.
  const visited=new Uint8Array(44*44);let largest=[];
  for(let index=0;index<44*44;index++)if(!visited[index]&&data[index*4+3]){
   const component=[index];visited[index]=1;
   for(let q=0;q<component.length;q++){const at=component[q],x=at%44,y=Math.floor(at/44);for(let yy=Math.max(0,y-1);yy<=Math.min(43,y+1);yy++)for(let xx=Math.max(0,x-1);xx<=Math.min(43,x+1);xx++){const next=yy*44+xx;if(!visited[next]&&data[next*4+3]){visited[next]=1;component.push(next);}}}
   if(component.length>largest.length)largest=component;
  }
  const keep=new Set(largest);minX=44;maxX=0;minY=44;maxY=0;
  for(let i=0;i<44*44;i++){if(!keep.has(i)){data.fill(0,i*4,i*4+4);continue;}const x=i%44,y=Math.floor(i/44);minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);}
  if(minY>maxY)throw Error('Empty sprite cell');
  let footMin=44,footMax=0;
  for(let y=Math.max(0,maxY-3);y<=maxY;y++)for(let x=0;x<44;x++)if(data[(y*44+x)*4+3]){footMin=Math.min(footMin,x);footMax=Math.max(footMax,x);}
  const dx=Math.max(-minX,Math.min(47-maxX,24-Math.round((footMin+footMax)/2))),dy=46-maxY;
  const aligned=Buffer.alloc(48*48*4);
  for(let y=minY;y<=maxY;y++)for(let x=minX;x<=maxX;x++){
   const source=(y*44+x)*4,target=((y+dy)*48+x+dx)*4;
   if(data[source+3])data.copy(aligned,target,source,source+4);
  }
  frames.push({role:groups[sheet][row],frame:column,data:aligned,alignment:{dx,dy,baseline:46}});
 }
}
// One weighted median-cut palette across all frames. Explicit 31 opaque colors
// plus transparent avoid encoder-dependent rounding to 256 palette entries.
const histogram=new Map();
for(const f of frames)for(let p=0;p<f.data.length;p+=4)if(f.data[p+3]){
 const key=(f.data[p]<<16)|(f.data[p+1]<<8)|f.data[p+2];histogram.set(key,(histogram.get(key)||0)+1);
}
const colors=[...histogram].map(([key,count])=>({key,rgb:[key>>16,(key>>8)&255,key&255],count}));
function range(bucket){return [0,1,2].map(c=>Math.max(...bucket.map(x=>x.rgb[c]))-Math.min(...bucket.map(x=>x.rgb[c])));}
const buckets=[colors];
while(buckets.length<31){
 let chosen=-1,best=-1,channel=0;
 for(let i=0;i<buckets.length;i++){if(buckets[i].length<2)continue;const ranges=range(buckets[i]),score=Math.max(...ranges);if(score>best){chosen=i;best=score;channel=ranges.indexOf(score);}}
 if(chosen<0)break;
 const bucket=buckets.splice(chosen,1)[0].sort((a,b)=>a.rgb[channel]-b.rgb[channel]),half=bucket.reduce((n,c)=>n+c.count,0)/2;
 let cut=1,total=0;for(let i=0;i<bucket.length-1;i++){total+=bucket[i].count;cut=i+1;if(total>=half)break;}
 buckets.push(bucket.slice(0,cut),bucket.slice(cut));
}
const palette=buckets.map(bucket=>{const weight=bucket.reduce((n,c)=>n+c.count,0);return [0,1,2].map(channel=>Math.round(bucket.reduce((n,c)=>n+c.rgb[channel]*c.count,0)/weight));});
const lookup=new Map();
for(const c of colors){let selected=palette[0],distance=Infinity;for(const color of palette){const d=color.reduce((n,v,i)=>n+(v-c.rgb[i])**2,0);if(d<distance){distance=d;selected=color;}}lookup.set(c.key,selected);}
const alignment=[];
for(let i=0;i<frames.length;i++){
 const frame=frames[i];await mkdir(out+'/'+frame.role,{recursive:true});
 const data=Buffer.from(frame.data);
 for(let p=0;p<data.length;p+=4)if(data[p+3]){const color=lookup.get((data[p]<<16)|(data[p+1]<<8)|data[p+2]);data[p]=color[0];data[p+1]=color[1];data[p+2]=color[2];}
 await sharp(data,{raw:{width:48,height:48,channels:4}}).png().toFile(out+'/'+frame.role+'/'+frame.frame+'.png');
 alignment.push({role:frame.role,frame:frame.frame,...frame.alignment});
}
await writeFile(out+'/provenance.json',JSON.stringify({
 revision:'task-keyframes-v2',tool:'built-in image_gen',character:'嘉然 / A-SOUL',created:'2026-10-19',
 roles:groups.flat(),keyframes_per_role:4,palette_limit:32,baseline:46,
 processing:'equal grid crop, connected-component cleanup, nearest-neighbor 44px into 48px canvas, feet anchor alignment, shared median-cut palette (31 opaque + transparent), hard alpha',
 scope:'AI-assisted fan reinterpretation; original character rights remain with their owners. Not official art.',alignment
},null,2));
console.log(JSON.stringify({roles:groups.flat(),keyframes:frames.length,out}));
