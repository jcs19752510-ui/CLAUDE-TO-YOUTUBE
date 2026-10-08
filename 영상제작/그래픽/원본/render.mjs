import {chromium} from '/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad/thumb/node_modules/playwright-core/index.mjs';
import fs from 'fs';
import path from 'path';
const dir=path.resolve(process.argv[2]);
const out=path.resolve(process.argv[3]);
const scenes={title:['01_타이틀카드',4],map:['02_오늘배울3가지',7],choose:['03_챗코워크코드_선택표',11],install:['04_설치3단계',7],login:['05_로그인_폴더신뢰',7],keys:['06_안전장치_키3개',8],mistakes:['07_초보실수3가지',10],cost:['08_비용기억클릭관리',8],summary:['09_5줄요약',11],end:['10_엔드카드_20초',20]};
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args:['--no-sandbox']});
for(const [id,[name,sec]] of Object.entries(scenes)){
  const vdir=path.join(out,'_tmp_'+id);fs.mkdirSync(vdir,{recursive:true});
  const ctx=await b.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:vdir,size:{width:1920,height:1080}}});
  const p=await ctx.newPage();
  await p.goto('file://'+dir+'/scenes.html?s='+id);
  await p.evaluate(()=>document.fonts.ready);
  await p.waitForTimeout(sec*1000);
  await p.screenshot({path:path.join(out,name+'.png')});
  await p.close();await ctx.close();
  const f=fs.readdirSync(vdir).find(x=>x.endsWith('.webm'));
  fs.renameSync(path.join(vdir,f),path.join(out,name+'.webm'));
  fs.rmdirSync(vdir);
  console.log(name,sec);
}
await b.close();
