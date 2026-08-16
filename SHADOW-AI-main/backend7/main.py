import hashlib, time
from fastapi import FastAPI
from pydantic import BaseModel, Field
app=FastAPI(title="Shadow AI Cache Jobs",version="1.0")
CACHE={}; MAX_ITEMS=100
class CacheRequest(BaseModel): key:str=Field(min_length=1,max_length=500); value:str=""; ttl:int=900
@app.get("/")
def root():return {"status":"cache service operational","items":len(CACHE)}
@app.get("/health")
def health():return {"status":"ok","items":len(CACHE)}
@app.post("/cache/set")
def set_cache(req:CacheRequest):
    if len(CACHE)>=MAX_ITEMS and req.key not in CACHE: CACHE.pop(next(iter(CACHE)))
    CACHE[req.key]={"value":req.value,"expires":time.time()+max(10,min(86400,req.ttl))}; return {"ok":True}
@app.get("/cache/get")
def get_cache(key:str):
    item=CACHE.get(key)
    if not item:return {"hit":False}
    if item["expires"]<time.time():CACHE.pop(key,None);return {"hit":False}
    return {"hit":True,"value":item["value"]}
