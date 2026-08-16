import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from fastapi import FastAPI
from pydantic import BaseModel, Field
from core.research_engine import ResearchEngine
app=FastAPI(title="Shadow AI Research Engine",version="1.0")
engine=ResearchEngine()
class ResearchRequest(BaseModel):
    query:str=Field(min_length=1,max_length=2000)
    max_sources:int=10
@app.get("/")
def root(): return {"status":"research engine operational","version":"1.0"}
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/research")
def research(req:ResearchRequest):
    evidence,sources=engine.research(req.query,max_sources=max(1,min(12,req.max_sources)))
    return {"query":req.query,"evidence":evidence,"sources":sources}
