import {chromium} from '/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad/thumb/node_modules/playwright-core/index.mjs';
import path from 'path';import {fileURLToPath} from 'url';
const d=path.dirname(fileURLToPath(import.meta.url));
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args:['--no-sandbox']});
const names={A:'썸네일_A_남색_홍보글7개',B:'썸네일_B_밝은회색_자동화3개',C:'썸네일_C_주황_코딩0줄'};
for(const k of ['A','B','C']){
  const p=await b.newPage({viewport:{width:1280,height:720}});
  await p.goto('file://'+d+'/thumbs.html');
  await p.evaluate(k=>{document.body.className=k;document.querySelectorAll('.t').forEach(e=>e.style.display=e.id===k?'block':'none')},k);
  await p.evaluate(()=>document.fonts.ready);
  await p.screenshot({path:d+'/../'+names[k]+'.png'});
  await p.screenshot({path:d+'/../'+names[k]+'.jpg',type:'jpeg',quality:92});
  console.log(k,'ok');
}
await b.close();
