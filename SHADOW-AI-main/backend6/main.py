import os, requests
from fastapi import FastAPI
from pydantic import BaseModel, Field
app=FastAPI(title="Shadow AI Context Engine",version="1.0")
OPENAI=os.getenv("OPENAI_API_KEY","").strip(); MODEL=os.getenv("OPENAI_MODEL","gpt-5")
class CompactRequest(BaseModel): text:str=Field(min_length=1,max_length=50000); target_chars:int=6000
@app.get("/")
def root():return {"status":"context engine operational","provider":"openai" if OPENAI else "local"}
@app.get("/health")
def health():return {"status":"ok"}
@app.post("/compact")
def compact(req:CompactRequest):
    target=max(1500,min(12000,req.target_chars))
    if OPENAI:
        try:
            r=requests.post("https://api.openai.com/v1/responses",headers={"Authorization":f"Bearer {OPENAI}","Content-Type":"application/json"},json={"model":MODEL,"instructions":"Compress the supplied conversation into a durable context summary. Preserve goals, decisions, facts, preferences, unresolved tasks and important technical details. Remove repetition.","input":req.text,"max_output_tokens":1800,"store":False},timeout=35); r.raise_for_status(); out=r.json().get("output_text")
            if out:return {"summary":out[:target],"compressed":True}
        except Exception as e:print("[context]",e)
    return {"summary":req.text[-target:],"compressed":False}
