#!/usr/bin/env python3
"""Objective grader for the personal-20 suite.

For each label (out/<label>/<id>.txt):
  - check=py   : extract the Python code, append a per-id test harness, run it
                 in a subprocess; PASS iff it exits 0.
  - check=rust : extract Rust, compile with `rustc --edition 2021 --crate-type lib`.
  - check=judge: skipped here (read by hand).

Tries multiple code-block reconstructions (concatenated / largest / last) and
accepts if ANY passes — to absorb models that split impl + example blocks.

Usage: grade_personal.py <label> [<label> ...]
"""
from __future__ import annotations
import json, pathlib, re, sys

import _exec

HERE = pathlib.Path(__file__).resolve().parent
SCEN = {s["id"]: s for s in json.loads((HERE / "scenarios_personal.json").read_text())["scenarios"]}


def blocks(text, lang):
    pat = r"```(?:%s)?\s*\n(.*?)```" % lang
    fences = re.findall(pat, text, re.DOTALL)
    if not fences:
        m = re.search(r"```(?:%s)?\s*\n(.*)" % lang, text, re.DOTALL)
        if m:
            fences = [m.group(1)]
    return fences


def py_candidates(text):
    fc = blocks(text, "python|py")
    code = [b for b in fc if "def " in b or "class " in b or "import " in b] or fc or [text]
    cands = []
    cands.append("\n\n".join(code))      # all blocks concatenated
    cands.append(max(code, key=len))      # largest block
    cands.append(code[-1])                # last block
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def rust_candidates(text, prefer_last):
    fc = blocks(text, "rust|rs")
    code = [b for b in fc if "fn " in b or "impl " in b or "struct " in b] or fc or [text]
    cands = []
    if prefer_last:
        cands.append(code[-1])
    cands.append("\n\n".join(code))
    cands.append(max(code, key=len))
    cands.append(code[-1])
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def run_py(code, test):
    """Pass/short-error wrapper over _exec.run_python (last stderr line, 120 chars)."""
    ok, err = _exec.run_python(code, test)
    if ok:
        return True, ""
    line = (err.strip().splitlines() or ["(no stderr)"])[-1]
    return False, line[:120]


def run_rust(code):
    """Pass/short-error wrapper over _exec.compile_rust (first error line, 120 chars)."""
    ok, err = _exec.compile_rust(code)
    if ok:
        return True, ""
    first = next((ln for ln in err.splitlines() if ln.startswith("error")), "")
    return False, first.strip()[:120]


# ---------------------------------------------------------------- tests
TESTS = {
"ml-01": r'''
import math
def _ident(d): return [[1.0 if i==j else 0.0 for j in range(d)] for i in range(d)]
def _ref(x, n_heads, causal):
    seq=len(x); d=len(x[0]); dh=d//n_heads
    out=[[0.0]*d for _ in range(seq)]
    for h in range(n_heads):
        cols=list(range(h*dh,(h+1)*dh))
        for i in range(seq):
            sc=[]
            for j in range(seq):
                if causal and j>i: sc.append(None); continue
                sc.append(sum(x[i][c]*x[j][c] for c in cols)/math.sqrt(dh))
            mx=max(s for s in sc if s is not None)
            ex=[math.exp(s-mx) if s is not None else 0.0 for s in sc]
            Z=sum(ex); w=[e/Z for e in ex]
            for c in cols:
                out[i][c]=sum(w[j]*x[j][c] for j in range(seq))
    return out
x=[[0.1,0.2,0.3,0.4],[0.5,-0.1,0.2,0.0],[-0.3,0.4,0.1,0.2]]
d=4
for nh in (1,2):
    for caus in (False,True):
        I=_ident(d)
        got=multihead_attention(x,I,I,I,I,nh,causal=caus)
        exp=_ref(x,nh,caus)
        assert len(got)==len(exp) and all(len(r)==d for r in got), "shape"
        for gi,ei in zip(got,exp):
            for gv,ev in zip(gi,ei):
                assert abs(gv-ev)<1e-6, (nh,caus,gv,ev)
''',
"ml-02": r'''
logits=[2.0,1.0,0.5,0.1,-1.0]
assert topk_topp_filter(logits,0,0.9)=={0,1,2,3}, topk_topp_filter(logits,0,0.9)
assert topk_topp_filter(logits,2,1.0)=={0,1}, topk_topp_filter(logits,2,1.0)
assert topk_topp_filter(logits,0,0.5)=={0}, topk_topp_filter(logits,0,0.5)
''',
"ml-03": r'''
kv=[[[1,2]],[[3,4]]]
out=repeat_kv(kv,2)
assert out==[[[1,2]],[[1,2]],[[3,4]],[[3,4]]], out
out[0][0][0]=999
assert kv[0][0][0]==1, "must not mutate/alias input"
assert repeat_kv(kv,1)==[[[1,2]],[[3,4]]]
''',
"ml-04": r'''
import math
v=[1.0,2.0,3.0,4.0]
r0=apply_rope(v,0)
for a,b in zip(r0,v): assert abs(a-b)<1e-9, ("pos0 identity",a,b)
d=4; pos=1; base=10000.0
th0=pos/base**(0/d); th1=pos/base**(2/d)
exp=[1*math.cos(th0)-3*math.sin(th0), 2*math.cos(th1)-4*math.sin(th1),
     1*math.sin(th0)+3*math.cos(th0), 2*math.sin(th1)+4*math.cos(th1)]
got=apply_rope(v,1)
for a,b in zip(got,exp): assert abs(a-b)<1e-6, (a,b)
''',
"py-02": r'''
stream=b"event: msg\ndata: hello\ndata: world\n\n: comment\ndata: bye\n\n"
p=SSEParser(); ev=[]
i=0
while i<len(stream):
    ev+=p.feed(stream[i:i+3]); i+=3
assert ev==[{'event':'msg','data':'hello\nworld'},{'event':None,'data':'bye'}], ev
''',
"py-03": r'''
import tempfile, os, json
d=tempfile.mkdtemp(); path=os.path.join(d,"state.json")
obj={'a':1,'b':[1,2,3],'c':{'x':True}}
atomic_write_json(path,obj)
assert read_json(path)==obj
left=os.listdir(d)
assert left==['state.json'], ("leftover temp files", left)
''',
"py-04": r'''
ns,extras=parse(['serve','m','--serve-arg=--foo','--serve-arg','bar','--port','9001','--allow-network','--','x','--y'])
assert ns.name=='m', ns.name
assert ns.port==9001, ns.port
assert ns.serve_arg==['--foo','bar'], ns.serve_arg
assert ns.allow_network is True
clean=[e for e in extras if e!='--']
assert clean==['x','--y'], extras
''',
"cc-01": r'''
req={'model':'m','system':'You are X','max_tokens':100,'temperature':0.5,
 'messages':[{'role':'user','content':'hi'},
   {'role':'assistant','content':[{'type':'text','text':'a'},{'type':'text','text':'b'},
                                  {'type':'tool_use','id':'1','name':'t','input':{}}]}],
 'tools':[{'name':'get','description':'d','input_schema':{'type':'object','properties':{}}}]}
o=anthropic_to_openai(req)
m=o['messages']
assert m[0]=={'role':'system','content':'You are X'}, m[0]
assert m[1]['role']=='user' and m[1]['content']=='hi', m[1]
assert m[2]['role']=='assistant' and m[2]['content']=='ab', m[2]
assert o['max_tokens']==100 and abs(o['temperature']-0.5)<1e-9
assert o.get('model')=='m'
t=o['tools'][0]
assert t['type']=='function'
assert t['function']['name']=='get' and t['function']['description']=='d'
assert t['function']['parameters']=={'type':'object','properties':{}}, t['function']['parameters']
''',
"cc-02": r'''
st=StreamTranslator(); ev=[]
ev+=st.feed({'choices':[{'delta':{'content':'Hel'},'finish_reason':None}]})
ev+=st.feed({'choices':[{'delta':{'content':'lo'},'finish_reason':None}]})
ev+=st.feed({'choices':[{'delta':{},'finish_reason':'stop'}]})
ev+=st.done()
types=[e['type'] for e in ev]
assert types==['message_start','content_block_start','content_block_delta',
               'content_block_delta','content_block_stop','message_delta','message_stop'], types
texts=[e['delta']['text'] for e in ev if e['type']=='content_block_delta']
assert texts==['Hel','lo'], texts
md=[e for e in ev if e['type']=='message_delta'][0]
assert md['delta']['stop_reason']=='end_turn', md
''',
"cc-03": r'''
items=list(range(50))
res=run_pipeline(items,4,lambda x:x*x)
assert res==[x*x for x in items], res[:10]
''',
"cc-04": r'''
import asyncio
def build():
    async def ok(i,delay):
        await asyncio.sleep(delay); return i
    async def boom():
        await asyncio.sleep(0.01); raise ValueError("boom")
    return [ok(0,0.01), ok(1,0.5), ok(2,0.02), boom()]
async def _main():
    return await gather_bounded(build(),2,0.2)
r=asyncio.run(_main())
assert r[0]==0, r
assert r[1]=='TIMEOUT', r
assert r[2]==2, r
assert isinstance(r[3],ValueError), r
''',
"fe-03": r'''
_csv_text="region,product,amount\nEU,A,10\nEU,B,5\nUS,A,3\n\nEU,A,2\n"
out=pivot(_csv_text)
assert out=={'EU':{'A':12,'B':5},'US':{'A':3}}, out
''',
"fe-04": r'''
a="alpha\nbeta\ngamma"
b="alpha\ndelta\ngamma"
res=unified_diff(a,b)
lines=res.split('\n')
ra=[l[1:] for l in lines if l and l[0] in ' -']
rb=[l[1:] for l in lines if l and l[0] in ' +']
assert '\n'.join(ra)==a, ("reconstruct a", ra)
assert '\n'.join(rb)==b, ("reconstruct b", rb)
assert any(l=='-beta' for l in lines) and any(l=='+delta' for l in lines), lines
''',
}


def main():
    labels = sys.argv[1:]
    if not labels:
        sys.exit("usage: grade_personal.py <label> [<label> ...]")
    summary = {}
    for label in labels:
        out = HERE / "out" / label
        print(f"\n## {label}")
        rows = {}
        for sid, s in SCEN.items():
            f = out / f"{sid}.txt"
            chk = s["check"]
            if not f.exists():
                print(f"  {sid:7} [{chk:5}] (no output)"); rows[sid] = None; continue
            text = f.read_text()
            if chk == "judge":
                print(f"  {sid:7} [judge] -> manual"); rows[sid] = "judge"; continue
            ok, err = False, "no candidate"
            if chk == "py":
                for c in py_candidates(text):
                    ok, err = run_py(c, TESTS[sid])
                    if ok: break
            elif chk == "rust":
                for c in rust_candidates(text, prefer_last=(sid == "rs-04")):
                    ok, err = run_rust(c)
                    if ok: break
            rows[sid] = ok
            print(f"  {sid:7} [{chk:5}] {'PASS ✅' if ok else 'FAIL ❌  ' + err}")
        gradable = [v for v in rows.values() if isinstance(v, bool)]
        passed = sum(1 for v in gradable if v)
        print(f"  -> objective {passed}/{len(gradable)} (excludes {sum(1 for v in rows.values() if v=='judge')} judged)")
        summary[label] = (passed, len(gradable))
    print("\n# SUMMARY (objective pass-rate)")
    for label, (p, n) in summary.items():
        print(f"  {label:24} {p}/{n}")


if __name__ == "__main__":
    main()
