import os, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
app=FastAPI(title="Shadow AI Judge",version="1.0")
OPENAI=os.getenv("OPENAI_API_KEY","").strip(); ANTHROPIC=os.getenv("ANTHROPIC_API_KEY","").strip()
OPENAI_MODEL=os.getenv("OPENAI_MODEL","gpt-5"); ANTHROPIC_MODEL=os.getenv("ANTHROPIC_MODEL","claude-sonnet-4-5")
class JudgeRequest(BaseModel):
    request:str=Field(min_length=1,max_length=6000); draft:str=Field(min_length=1,max_length=16000); evidence:str=""; royal_mode:bool=False

def ask_openai(prompt):
    if not OPENAI:return None
    try:
        r=requests.post("https://api.openai.com/v1/responses",headers={"Authorization":f"Bearer {OPENAI}","Content-Type":"application/json"},json={"model":OPENAI_MODEL,"instructions":"Audit an AI answer for factual accuracy, unsupported claims, logical errors and missing caveats. Return a corrected final answer only.","input":prompt,"max_output_tokens":1500},timeout=30); r.raise_for_status(); return r.json().get("output_text")
    except Exception as e: print("[judge/openai]",e); return None

def ask_anthropic(prompt):
    if not ANTHROPIC:return None
    try:
        r=requests.post("https://api.anthropic.com/v1/messages",headers={"x-api-key":ANTHROPIC,"anthropic-version":"2023-06-01","content-type":"application/json"},json={"model":ANTHROPIC_MODEL,"max_tokens":1500,"system":"Audit and correct an AI answer. Return a final corrected answer only.","messages":[{"role":"user","content":prompt}]},timeout=30); r.raise_for_status(); return "\n".join(x.get("text","") for x in r.json().get("content",[]) if x.get("type")=="text")
    except Exception as e: print("[judge/anthropic]",e); return None
@app.get("/")
def root():return {"status":"judge operational","providers":{"openai":bool(OPENAI),"anthropic":bool(ANTHROPIC)}}
@app.get("/health")
def health():return {"status":"ok"}
@app.post("/judge")
def judge(req:JudgeRequest):
    prompt=f"REQUEST:\n{req.request}\n\nEVIDENCE:\n{req.evidence or '[none]'}\n\nDRAFT:\n{req.draft}\n\nCheck every important claim. If evidence is weak, state uncertainty. Preserve useful details."
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs=[pool.submit(ask_openai,prompt),pool.submit(ask_anthropic,prompt)]
        answers=[]
        for f in as_completed(fs):
            try:
                value=f.result()
                if value: answers.append(value)
            except Exception as exc:
                print("[judge/worker]", exc)
    if not answers: return {"response":req.draft,"audited":False}
    if len(answers)==1:return {"response":answers[0],"audited":True}
    if OPENAI and os.getenv("JUDGE_RECONCILE","1") == "1":
        reconcile=("Reconcile two independent audits into one final answer. Keep only claims supported by the evidence. "
                   "Return the corrected answer only.\n\nREQUEST:\n"+req.request+"\n\nEVIDENCE:\n"+req.evidence+"\n\nAUDIT A:\n"+answers[0]+"\n\nAUDIT B:\n"+answers[1])
        final=ask_openai(reconcile)
        if final:return {"response":final,"audited":True,"audits":2}
    return {"response":answers[0],"alternatives":answers[1:],"audited":True,"audits":2}
