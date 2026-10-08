// 사용: node render.mjs <출력루트(그래픽)> [챕터번호들 예: 1,2]
import {chromium} from '/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad/thumb/node_modules/playwright-core/index.mjs';
import fs from 'fs';import path from 'path';import {execSync} from 'child_process';
const here=path.dirname(new URL(import.meta.url).pathname);
const root=path.resolve(process.argv[2]);
const only=process.argv[3]?process.argv[3].split(','):null;
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args:['--no-sandbox']});
const lp=await b.newPage({viewport:{width:1920,height:1080}});
await lp.goto('file://'+here+'/cards.html?c=list');
const list=JSON.parse(await lp.title());await lp.close();
fs.mkdirSync(root+'/이미지_png',{recursive:true});fs.mkdirSync(root+'/영상_mp4',{recursive:true});
const tmp=root+'/원본/_tmp';fs.mkdirSync(tmp,{recursive:true});
const chs=[...new Set(list.map(x=>x[0].split('_')[0]))];
for(const ch of chs){
  if(only&&!only.includes(ch))continue;
  const items=list.filter(x=>x[0].startsWith(ch+'_'));
  const ctx=await b.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:tmp,size:{width:1920,height:1080}}});
  const p=await ctx.newPage();
  const marks=[];const t0=Date.now();
  for(const [id,name,sec] of items){
    await p.goto('file://'+here+'/cards.html?c='+id);
    await p.evaluate(()=>document.fonts.ready);
    marks.push((Date.now()-t0)/1000);
    await p.waitForTimeout(Math.min(sec,6)*1000>3500?3500:sec*1000>3500?3500:3500);
    await p.screenshot({path:`${root}/이미지_png/${id}_${name}.png`});
    await p.waitForTimeout(sec*1000-3500>0?sec*1000-3500:0);
    console.log(id,name);
  }
  await p.close();await ctx.close();
  const f=fs.readdirSync(tmp).find(x=>x.endsWith('.webm'));
  const wp=`${tmp}/G0${ch}.webm`;fs.renameSync(`${tmp}/${f}`,wp);
  execSync(`ffmpeg -loglevel error -y -ss 0.4 -i "${wp}" -r 30 -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart -an "${root}/영상_mp4/G0${ch}.mp4"`);
  fs.unlinkSync(wp);
}
await b.close();fs.rmSync(tmp,{recursive:true,force:true});
