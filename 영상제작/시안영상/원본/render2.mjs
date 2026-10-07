import {chromium} from '/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad/thumb/node_modules/playwright-core/index.mjs';
import fs from 'fs';import path from 'path';
const S=process.argv[3];
const segs=JSON.parse(fs.readFileSync(S+'/segs.json','utf8'));
const html='file://'+path.resolve(process.argv[2])+'/card.html';
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args:['--no-sandbox']});
const p=await b.newPage({viewport:{width:1280,height:720}});
let i=0;
for(const [k,v,dur] of segs){
  if(k==='card'){
    const q=new URLSearchParams({tag:v.tag,tm:v.tm,cap:v.cap,src:v.src});
    await p.goto(html+'?'+q.toString());
    await p.evaluate(()=>document.fonts.ready);
    await p.screenshot({path:`${S}/c${String(i).padStart(3,'0')}.png`});
  }
  i++;
}
await b.close();console.log('rendered',i);
