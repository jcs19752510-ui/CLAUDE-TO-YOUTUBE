import json,subprocess,os,sys,urllib.parse,re
S="/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad/anim"
os.makedirs(S,exist_ok=True)
d=json.load(open("/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad/narr.json",encoding="utf8"))
G="/home/user/CLAUDE-TO-YOUTUBE/영상제작/그래픽/영상_mp4/"
src={"①":"얼굴:A1|화면녹화:B1·B2","②":"얼굴:A2","③":"얼굴:A3|화면녹화:B3","④":"얼굴:A4|화면녹화:B4·B5","⑤":"얼굴:A5|화면녹화:B6·B7","⑥":"얼굴:A6|화면녹화:B8","⑦":"얼굴:A7|화면녹화:B9","⑧":"얼굴:A8|화면녹화:B10","⑨":"얼굴:A9|화면녹화:B11","⑩":"얼굴:A10"}
# graphic insert: (chapter, position) -> list of files ; position 'start'/'end'/index after paragraph
ins={("①","end"):["01_타이틀카드"],("②","end"):["02_오늘배울3가지"],("③","end"):["03_챗코워크코드_선택표"],
("④","start"):["04_설치3단계"],("④","end"):["05_로그인_폴더신뢰"],("⑧","start"):["06_안전장치_키3개"],("⑧","end"):["07_초보실수3가지"],
("⑨","start"):["08_비용기억클릭관리"],("⑩","mid"):["09_5줄요약"],("⑩","end"):["10_엔드카드_20초"]}
segs=[] # (kind,path/params,dur)
def card(tag,tm,cap,srcs):
    segs.append(("card",dict(tag=tag,tm=tm,cap=cap,src=srcs),max(3.0,len(cap)/4.8+0.8)))
def gfx(name): segs.append(("gfx",G+name+".mp4",None))
chap_start=[]
for c in d["order"]:
    cid,title,s,e=c
    paras=d["out"][cid]
    tag=f"{cid} {title.replace(' ⭐','')}"
    for g in ins.get((cid,"start"),[]): gfx(g)
    half=len(paras)//2
    for i,x in enumerate(paras):
        card(tag,f"대본 {s}~{e}",x,src[cid])
        if cid=="⑩" and i==half-1:
            for g in ins[("⑩","mid")]: gfx(g)
    for g in ins.get((cid,"end"),[]): gfx(g)
json.dump(segs,open(S+"/segs.json","w"),ensure_ascii=False)
print(len(segs),"segments")
