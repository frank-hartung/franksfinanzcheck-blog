import sys, re, pathlib, unicodedata
sys.path.insert(0,'/home/user/franksfinanzcheck-blog/scripts')
import faktenfrische_befund_ledger as L
STOP=set("der die das und oder aber ist sind war wird werden ein eine einen einem eines für mit von zu im in am an auf aus bei dass als auch nicht nur noch sich den dem des sie wir dir du ich er es kann können muss müssen soll sollen etwa rund laut wie jetzt schon immer mehr sehr alle alles diese dieser dieses".split())
def toks(s):
    s=unicodedata.normalize('NFKC',s).lower()
    return [w for w in re.findall(r'[a-zäöüß0-9%€]+', s) if len(w)>3 and w not in STOP]
def path_for(slug):
    p=pathlib.Path('/home/user/franksfinanzcheck-blog/content/posts')/slug/'index.md'
    if p.exists(): return p
    hits=sorted(pathlib.Path('/home/user/franksfinanzcheck-blog/content').rglob(f'{slug}*/index.md'))+sorted(pathlib.Path('/home/user/franksfinanzcheck-blog/content').rglob(f'*{slug}*/index.md'))
    return hits[0] if hits else None
for slug in sys.argv[1:]:
    es=[e for e in L.befunde_mit_status() if e['slug'].startswith(slug)]
    p=path_for(slug); body=(p.read_text(encoding='utf-8').split('---',2)[2] if p else '')
    lines=body.splitlines()
    print("###",slug,len(es),"Befunde")
    for e in es:
        print(f"- {e['id']} {e['typ']} {e['fassung_status']}: {e['text'][:200]}")
        ft=set(toks(e['text'])); sc=[]
        for i,ln in enumerate(lines):
            if ln.strip():
                n=len(ft & set(toks(ln)))
                if n: sc.append((n,i,ln))
        sc.sort(key=lambda x:-x[0])
        for n,i,ln in sc[:2]: print(f"    L{i+1} {ln.strip()[:190]}")
