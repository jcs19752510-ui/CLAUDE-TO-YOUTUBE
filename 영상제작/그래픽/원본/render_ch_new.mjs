import {chromium} from '/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad/thumb/node_modules/playwright-core/index.mjs';
import fs from 'fs';import path from 'path';
const dir=path.resolve(process.argv[2]);const out=path.resolve(process.argv[3]);
const items=[
['11_챕터01_하이라이트',{n:'1',t:'하이라이트',s:'말 한 줄로 완성'}],
['11_챕터02_통증과약속',{n:'2',t:'통증 + 약속',s:'터미널 없이, 앱 하나로'}],
['11_챕터03_설치와로그인',{n:'3',t:'설치와 로그인',s:'공식 사이트에서만'}],
['11_챕터04_세개의탭',{n:'4',t:'챗 · 코워크 · 코드',s:'결과물이 뭐냐?'}],
['11_챕터05_챗',{n:'5',t:'챗 Chat',s:'답을 얻는다'}],
['11_챕터06_코워크',{n:'6',t:'코워크 Cowork',s:'일을 맡긴다'}],
['11_챕터07_코드탭첫세션',{n:'7',t:'코드 탭 첫 세션',s:'말로 시키고 허락하기'}],
['11_챕터08_권한모드와플랜',{n:'8',t:'권한 모드와 플랜',s:'처음엔 Manual'}],
['11_챕터09_더잘쓰는법',{n:'9',t:'더 잘 쓰는 5가지',s:'멈추기 · @파일 · 지침서'}],
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
