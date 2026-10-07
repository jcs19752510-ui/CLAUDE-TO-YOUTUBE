import {chromium} from '/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad/thumb/node_modules/playwright-core/index.mjs';
import fs from 'fs';import path from 'path';
const dir=path.resolve(process.argv[2]);const out=path.resolve(process.argv[3]);
const items=[
['11_챕터01_하이라이트',{n:'1',t:'하이라이트',s:'완성된 결과부터'}],
['11_챕터02_통증과약속',{n:'2',t:'통증 + 약속',s:'AI를 반만 쓰고 있다면'}],
['11_챕터03_챗코워크코드',{n:'3',t:'챗 · 코워크 · 코드',s:'결과물이 뭐냐?'}],
['11_챕터04_설치와로그인',{n:'4',t:'설치와 로그인',s:'3단계면 끝'}],
['11_챕터05_첫프로젝트',{n:'5',t:'첫 프로젝트',s:'말로만 만들어 보기'}],
['11_챕터06_CLAUDEMD',{n:'6',t:'CLAUDE.md',s:'클로드의 업무 지침서'}],
['11_챕터07_플랜모드',{n:'7',t:'플랜 모드',s:'어려울수록 계획 먼저'}],
['11_챕터08_안전장치',{n:'8',t:'안전장치 + 실수 3가지',s:'되돌리는 법'}],
['11_챕터09_비용기억',{n:'9',t:'비용 · 기억 관리',s:'아끼고, 줄이고'}],
['11_챕터10_마무리',{n:'10',t:'요약 + 오늘 할 일',s:'딱 하나만 하세요'}],
['12_AI음성고지카드',{k:'box',h:'안내',p:'이 영상의 목소리는 AI 음성입니다.|화면 시연은 직접 녹화한 실제 화면입니다.'}]
];
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args:['--no-sandbox']});
for(const [name,params] of items){
  const vdir=path.join(out,'_t');fs.mkdirSync(vdir,{recursive:true});
  const ctx=await b.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:vdir,size:{width:1920,height:1080}}});
  const p=await ctx.newPage();
  await p.goto('file://'+dir+'/chapter.html?'+new URLSearchParams(params).toString());
  await p.evaluate(()=>document.fonts.ready);
  await p.waitForTimeout(3500);
  await p.screenshot({path:path.join(out,name+'.png')});
  await p.close();await ctx.close();
  const f=fs.readdirSync(vdir).find(x=>x.endsWith('.webm'));
  fs.renameSync(path.join(vdir,f),path.join(out,name+'.webm'));
  fs.rmdirSync(vdir);console.log(name);
}
await b.close();
