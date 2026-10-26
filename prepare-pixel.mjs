// Production sprite slicing / palette conversion; never alters the source artwork.
import sharp from 'sharp';
import {mkdir,copyFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('.',import.meta.url));
const input=process.argv[2];
if(!input)throw Error('Provide the generated source PNG path');
const ident=process.argv[3]||'diana';
if(!/^[a-z0-9-]+$/.test(ident))throw Error('Invalid character ID');
const out=root+'artwork/pixel-'+ident;
await mkdir(out,{recursive:true});
await copyFile(input,out+'/source-sheet.png');
const meta=await sharp(input).metadata();
const w=meta.width/4,h=meta.height/2;
const frames=[];
for(let i=0;i<8;i++){
 const left=Math.round((i%4)*w),top=Math.round(Math.floor(i/4)*h);
 const width=Math.round((i%4+1)*w)-left,height=Math.round((Math.floor(i/4)+1)*h)-top;
 const {data,info}=await sharp(input).extract({left,top,width,height})
  .resize(44,44,{kernel:'nearest'}).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 // Hard alpha + limited palette retain a true small pixel grid, no fuzzy matte.
 for(let p=0;p<data.length;p+=4){data[p+3]=data[p+3]>=160?255:0;if(!data[p+3])data.fill(0,p,p+4);}
 const visited=new Uint8Array(44*44);let largest=[];
 for(let j=0;j<44*44;j++)if(!visited[j]&&data[j*4+3]){
  const component=[j];visited[j]=1;
  for(let q=0;q<component.length;q++){
   const at=component[q],x=at%44,y=Math.floor(at/44);
   for(let yy=Math.max(0,y-1);yy<=Math.min(43,y+1);yy++)for(let xx=Math.max(0,x-1);xx<=Math.min(43,x+1);xx++){
    const next=yy*44+xx;if(!visited[next]&&data[next*4+3]){visited[next]=1;component.push(next);}
   }
  }
  if(component.length>largest.length)largest=component;
 }
 if(largest.length<60)throw Error('Missing character in sprite cell '+i);
 const minX=Math.min(...largest.map(p=>p%44)),maxX=Math.max(...largest.map(p=>p%44)),maxY=Math.max(...largest.map(p=>Math.floor(p/44)));
 const dx=24-Math.round((minX+maxX)/2),dy=46-maxY,aligned=Buffer.alloc(48*48*4);
 for(const p of largest){const x=p%44+dx,y=Math.floor(p/44)+dy;data.copy(aligned,(y*48+x)*4,p*4,p*4+4);}
 frames.push(aligned);
}
// One shared palette for every expression, so faces and outfits do not flicker.
const histogram=new Map();
for(const data of frames)for(let p=0;p<data.length;p+=4)if(data[p+3]){const key=(data[p]<<16)|(data[p+1]<<8)|data[p+2];histogram.set(key,(histogram.get(key)||0)+1);}
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
for(const color of colors){let best=palette[0],distance=Infinity;for(const candidate of palette){const value=candidate.reduce((n,v,i)=>n+(v-color.rgb[i])**2,0);if(value<distance){distance=value;best=candidate;}}lookup.set(color.key,best);}
for(let i=0;i<8;i++){
 const data=frames[i];for(let p=0;p<data.length;p+=4)if(data[p+3]){const color=lookup.get((data[p]<<16)|(data[p+1]<<8)|data[p+2]);data[p]=color[0];data[p+1]=color[1];data[p+2]=color[2];}
 await sharp(data,{raw:{width:48,height:48,channels:4}}).png().toFile(out+'/pose-'+i+'.png');
}
await writeFile(out+'/provenance.json',JSON.stringify({
 character:ident,method:'AI-assisted pixel reinterpretation; not original official sprite art',
 tool:'built-in image_gen',source_reference:'../'+ident+'.png',generated_on:'2026-10-19',
 processing:'4x2 equal-cell slicing, largest connected character, 44px nearest-neighbor into 48px canvas, binary alpha, baseline 46, shared maximum 32-color palette',
 prompt:'prompt.txt',rights:'Character rights remain with the original rights holders. Unofficial noncommercial fan work.'
},null,2));
console.log(JSON.stringify({frames:8,size:48,folder:out}));
