#!/usr/bin/env python3
"""Write reference 'gold' solutions to out/_gold/<id>.txt to self-test the grader."""
import pathlib
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out" / "_gold"; OUT.mkdir(parents=True, exist_ok=True)

PY = {
"ml-01": '''import math
def multihead_attention(x, w_q, w_k, w_v, w_o, n_heads, causal=False):
    seq=len(x); d=len(x[0]); dh=d//n_heads
    def mm(A,B):
        return [[sum(A[i][k]*B[k][j] for k in range(len(B))) for j in range(len(B[0]))] for i in range(len(A))]
    Q=mm(x,w_q); K=mm(x,w_k); V=mm(x,w_v)
    out=[[0.0]*d for _ in range(seq)]
    for h in range(n_heads):
        cols=list(range(h*dh,(h+1)*dh))
        for i in range(seq):
            sc=[]
            for j in range(seq):
                if causal and j>i: sc.append(None); continue
                sc.append(sum(Q[i][c]*K[j][c] for c in cols)/math.sqrt(dh))
            mx=max(s for s in sc if s is not None)
            ex=[math.exp(s-mx) if s is not None else 0.0 for s in sc]
            Z=sum(ex); w=[e/Z for e in ex]
            for c in cols:
                out[i][c]=sum(w[j]*V[j][c] for j in range(seq))
    return mm(out,w_o)''',
"ml-02": '''import math
def topk_topp_filter(logits, top_k, top_p):
    idx=list(range(len(logits)))
    if top_k and top_k>0:
        idx=sorted(idx,key=lambda i:(-logits[i],i))[:top_k]
    mx=max(logits[i] for i in idx)
    ex={i:math.exp(logits[i]-mx) for i in idx}
    Z=sum(ex.values()); probs={i:ex[i]/Z for i in idx}
    order=sorted(idx,key=lambda i:(-probs[i],-logits[i],i))
    kept=set(); cum=0.0
    for i in order:
        kept.add(i); cum+=probs[i]
        if cum>=top_p: break
    return kept''',
"ml-03": '''def repeat_kv(kv, n_rep):
    out=[]
    for head in kv:
        for _ in range(n_rep):
            out.append([list(row) for row in head])
    return out''',
"ml-04": '''import math
def apply_rope(vec, pos, base=10000.0):
    d=len(vec); half=d//2
    x1=vec[:half]; x2=vec[half:]; o1=[0.0]*half; o2=[0.0]*half
    for i in range(half):
        th=pos/(base**(2*i/d)); c=math.cos(th); s=math.sin(th)
        o1[i]=x1[i]*c-x2[i]*s; o2[i]=x1[i]*s+x2[i]*c
    return o1+o2''',
"py-02": '''class SSEParser:
    def __init__(self): self.buf=b""
    def feed(self, chunk):
        self.buf+=chunk; events=[]
        while b"\\n\\n" in self.buf:
            raw,self.buf=self.buf.split(b"\\n\\n",1)
            ev=None; data=[]
            for line in raw.decode("utf-8").split("\\n"):
                if not line or line.startswith(":"): continue
                field,_,val=line.partition(":")
                if val.startswith(" "): val=val[1:]
                if field=="event": ev=val
                elif field=="data": data.append(val)
            events.append({"event":ev,"data":"\\n".join(data)})
        return events''',
"py-03": '''import json,os,tempfile
def atomic_write_json(path,obj):
    d=os.path.dirname(os.path.abspath(path)) or "."
    fd,tmp=tempfile.mkstemp(dir=d,suffix=".tmp")
    try:
        with os.fdopen(fd,"w") as f:
            json.dump(obj,f); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise
def read_json(path):
    with open(path) as f: return json.load(f)''',
"py-04": '''import argparse
def build_parser():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="cmd")
    s=sub.add_parser("serve"); s.add_argument("name")
    s.add_argument("--port",type=int,default=8000)
    s.add_argument("--serve-arg",action="append",default=[],dest="serve_arg")
    s.add_argument("--allow-network",action="store_true")
    return p
def parse(argv):
    if "--" in argv:
        i=argv.index("--"); main=argv[:i]; extras=argv[i+1:]
    else:
        main=argv; extras=[]
    return build_parser().parse_args(main), extras''',
"cc-01": '''def anthropic_to_openai(req):
    msgs=[]
    if isinstance(req.get("system"),str):
        msgs.append({"role":"system","content":req["system"]})
    for m in req.get("messages",[]):
        c=m.get("content")
        text="".join(b.get("text","") for b in c if b.get("type")=="text") if isinstance(c,list) else c
        msgs.append({"role":m.get("role"),"content":text})
    out={"model":req.get("model","default"),"messages":msgs}
    if "max_tokens" in req: out["max_tokens"]=req["max_tokens"]
    if "temperature" in req: out["temperature"]=req["temperature"]
    if "tools" in req:
        out["tools"]=[{"type":"function","function":{"name":t["name"],"description":t.get("description",""),"parameters":t.get("input_schema",{})}} for t in req["tools"]]
    return out''',
"cc-02": '''class StreamTranslator:
    def __init__(self): self.started=False; self.block=False; self.stopped=False
    def feed(self,chunk):
        ev=[]; ch=chunk["choices"][0]; delta=ch.get("delta",{}); text=delta.get("content")
        if not self.started: ev.append({"type":"message_start"}); self.started=True
        if text:
            if not self.block:
                ev.append({"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}); self.block=True
            ev.append({"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":text}})
        fr=ch.get("finish_reason")
        if fr is not None and not self.stopped:
            if self.block: ev.append({"type":"content_block_stop","index":0})
            sr={"stop":"end_turn","length":"max_tokens"}.get(fr,"end_turn")
            ev.append({"type":"message_delta","delta":{"stop_reason":sr}})
            ev.append({"type":"message_stop"}); self.stopped=True
        return ev
    def done(self):
        if not self.stopped:
            self.stopped=True; return [{"type":"message_stop"}]
        return []''',
"cc-03": '''import threading,queue
def run_pipeline(items,n_workers,process):
    q=queue.Queue(maxsize=max(1,n_workers*2)); results=[None]*len(items)
    def worker():
        while True:
            job=q.get()
            if job is None: q.task_done(); break
            i,item=job; results[i]=process(item); q.task_done()
    ts=[threading.Thread(target=worker) for _ in range(n_workers)]
    for t in ts: t.start()
    for i,item in enumerate(items): q.put((i,item))
    for _ in ts: q.put(None)
    for t in ts: t.join()
    return results''',
"cc-04": '''import asyncio
async def gather_bounded(coros,limit,timeout):
    sem=asyncio.Semaphore(limit); results=[None]*len(coros)
    async def runner(i,coro):
        async with sem:
            try: results[i]=await asyncio.wait_for(coro,timeout)
            except asyncio.TimeoutError: results[i]="TIMEOUT"
            except Exception as e: results[i]=e
    tasks=[asyncio.ensure_future(runner(i,c)) for i,c in enumerate(coros)]
    try: await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            if not t.done(): t.cancel()
    return results''',
"fe-03": '''import csv,io
def pivot(rows_csv):
    out={}; rows=list(csv.reader(io.StringIO(rows_csv)))
    for row in rows[1:]:
        if not row or all(c=="" for c in row): continue
        region,product,amount=row[0],row[1],int(row[2])
        out.setdefault(region,{})
        out[region][product]=out[region].get(product,0)+amount
    return out''',
"fe-04": '''def unified_diff(a,b):
    A=a.split("\\n"); B=b.split("\\n"); n,m=len(A),len(B)
    dp=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n-1,-1,-1):
        for j in range(m-1,-1,-1):
            dp[i][j]=dp[i+1][j+1]+1 if A[i]==B[j] else max(dp[i+1][j],dp[i][j+1])
    out=[]; i=j=0
    while i<n and j<m:
        if A[i]==B[j]: out.append(" "+A[i]); i+=1; j+=1
        elif dp[i+1][j]>=dp[i][j+1]: out.append("-"+A[i]); i+=1
        else: out.append("+"+B[j]); j+=1
    while i<n: out.append("-"+A[i]); i+=1
    while j<m: out.append("+"+B[j]); j+=1
    return "\\n".join(out)''',
}

RUST = {
"rs-01": '''use std::collections::HashMap;
use std::sync::Mutex;
pub struct LruCache<K, V> { inner: Mutex<Inner<K, V>>, capacity: usize }
struct Inner<K, V> { map: HashMap<K, V>, order: Vec<K> }
impl<K: std::hash::Hash + Eq + Clone, V: Clone> LruCache<K, V> {
    pub fn new(capacity: usize) -> Self {
        LruCache { inner: Mutex::new(Inner { map: HashMap::new(), order: Vec::new() }), capacity }
    }
    pub fn get(&self, k: &K) -> Option<V> {
        let mut g = self.inner.lock().unwrap();
        if let Some(v) = g.map.get(k).cloned() {
            g.order.retain(|x| x != k); g.order.push(k.clone()); Some(v)
        } else { None }
    }
    pub fn put(&self, k: K, v: V) {
        let mut g = self.inner.lock().unwrap();
        if g.map.contains_key(&k) { g.order.retain(|x| x != &k); }
        else if self.capacity > 0 && g.map.len() >= self.capacity {
            if !g.order.is_empty() { let old = g.order.remove(0); g.map.remove(&old); }
        }
        g.map.insert(k.clone(), v); g.order.push(k);
    }
}''',
"rs-02": '''pub struct Windows<'a, T> { slice: &'a [T], size: usize, pos: usize }
impl<'a, T> Windows<'a, T> {
    pub fn new(slice: &'a [T], size: usize) -> Self {
        assert!(size != 0, "size must be non-zero");
        Windows { slice, size, pos: 0 }
    }
}
impl<'a, T> Iterator for Windows<'a, T> {
    type Item = &'a [T];
    fn next(&mut self) -> Option<Self::Item> {
        if self.pos + self.size <= self.slice.len() {
            let w = &self.slice[self.pos..self.pos + self.size]; self.pos += 1; Some(w)
        } else { None }
    }
}''',
"rs-03": '''use std::collections::VecDeque;
use std::sync::{Arc, Condvar, Mutex};
struct Shared<T> { q: Mutex<(VecDeque<T>, usize)>, not_full: Condvar, not_empty: Condvar, cap: usize }
pub struct Sender<T> { s: Arc<Shared<T>> }
pub struct Receiver<T> { s: Arc<Shared<T>> }
pub fn channel<T>(capacity: usize) -> (Sender<T>, Receiver<T>) {
    let s = Arc::new(Shared { q: Mutex::new((VecDeque::new(), 1)), not_full: Condvar::new(), not_empty: Condvar::new(), cap: capacity });
    (Sender { s: s.clone() }, Receiver { s })
}
impl<T> Sender<T> {
    pub fn send(&self, value: T) {
        let mut g = self.s.q.lock().unwrap();
        while g.0.len() >= self.s.cap { g = self.s.not_full.wait(g).unwrap(); }
        g.0.push_back(value); self.s.not_empty.notify_one();
    }
}
impl<T> Clone for Sender<T> {
    fn clone(&self) -> Self { self.s.q.lock().unwrap().1 += 1; Sender { s: self.s.clone() } }
}
impl<T> Drop for Sender<T> {
    fn drop(&mut self) { let mut g = self.s.q.lock().unwrap(); g.1 -= 1; if g.1 == 0 { self.s.not_empty.notify_all(); } }
}
impl<T> Receiver<T> {
    pub fn recv(&self) -> Option<T> {
        let mut g = self.s.q.lock().unwrap();
        loop {
            if let Some(v) = g.0.pop_front() { self.s.not_full.notify_one(); return Some(v); }
            if g.1 == 0 { return None; }
            g = self.s.not_empty.wait(g).unwrap();
        }
    }
}''',
"rs-04": '''The bug: it returns `&owned`, a reference to a local `String` that is dropped at function end.

```rust
fn longest_word(text: &str) -> (&str, usize) {
    let mut best = "";
    for w in text.split_whitespace() {
        if w.len() > best.len() { best = w; }
    }
    (best, best.len())
}
```''',
}

for sid, code in PY.items():
    (OUT / f"{sid}.txt").write_text("```python\n" + code + "\n```\n")
for sid, code in RUST.items():
    body = code if sid == "rs-04" else "```rust\n" + code + "\n```\n"
    (OUT / f"{sid}.txt").write_text(body)
print(f"wrote {len(PY)+len(RUST)} gold files to {OUT}")
