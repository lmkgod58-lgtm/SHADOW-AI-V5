import os,time,uuid,requests
from threading import BoundedSemaphore
from typing import Dict,List,Optional
from fastapi import FastAPI,HTTPException,Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from core.ai_router import AIRouter
from core.code_validator import CodeValidator
from core.research_engine import ResearchEngine
from core.memory_client import MemoryClient
app=FastAPI(title="Shadow AI Main Brain",version="4.1")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
ai=AIRouter(); local_research=ResearchEngine(); validator=CodeValidator(); memory=MemoryClient()
RESEARCH_BACKEND_URL=os.getenv("RESEARCH_BACKEND_URL","").strip().rstrip("/"); JUDGE_BACKEND_URL=os.getenv("JUDGE_BACKEND_URL","").strip().rstrip("/")
MAX_HISTORY=int(os.getenv("MAX_HISTORY_MESSAGES","16")); CHAT_SLOTS=BoundedSemaphore(max(1,int(os.getenv("CHAT_CONCURRENCY","1"))))
class HistoryItem(BaseModel):
    role:str=Field(pattern="^(user|assistant|system)$"); content:str=Field(max_length=12000)
class ChatRequest(BaseModel):
    message:str=Field(min_length=1,max_length=12000); history:List[HistoryItem]=Field(default_factory=list); deep_search:bool=False; royal_mode:bool=False; memory_context:str=Field(default="",max_length=12000); user_id:str=Field(default="default",max_length=200); client_request_id:str=Field(default="",max_length=200)
def remote_research(q):
    if not RESEARCH_BACKEND_URL:return None,[]
    try:
        r=requests.post(RESEARCH_BACKEND_URL+"/research",json={"query":q,"max_sources":8},timeout=15); r.raise_for_status(); d=r.json(); return d.get("evidence",""),d.get("sources",[])
    except Exception as e: print("[Research remote]",type(e).__name__,e); return None,[]
def remote_judge(payload):
    if not JUDGE_BACKEND_URL:return None
    try:
        r=requests.post(JUDGE_BACKEND_URL+"/judge",json=payload,timeout=25); r.raise_for_status(); return r.json().get("response")
    except Exception as e: print("[Judge remote]",type(e).__name__,e); return None
@app.get("/")
def root():return {"status":"Shadow AI Main Brain operational","version":"4.1","ai":ai.status(),"research_backend":bool(RESEARCH_BACKEND_URL),"judge_backend":bool(JUDGE_BACKEND_URL)}
@app.get("/health")
def health():return {"status":"ok","ai":ai.status(),"memory":memory.enabled(),"research_backend":bool(RESEARCH_BACKEND_URL),"judge_backend":bool(JUDGE_BACKEND_URL)}
@app.get("/tools")
def tools():return {"local_terminal_tools":local_research.terminal_status(),"remote_research":bool(RESEARCH_BACKEND_URL),"remote_judge":bool(JUDGE_BACKEND_URL)}
@app.post("/research")
def research_endpoint(req:Dict):
    q=str(req.get("query","")).strip()
    if not q:raise HTTPException(400,"query is required")
    evidence,sources=local_research.research(q,max_sources=8);return {"query":q,"evidence":evidence,"sources":sources}
@app.post("/chat")
def chat(req:ChatRequest,x_client_request_id:Optional[str]=Header(default=None)):
    if not CHAT_SLOTS.acquire(timeout=5):raise HTTPException(429,"Shadow AI is busy processing another request. Please retry shortly.")
    rid=x_client_request_id or req.client_request_id or uuid.uuid4().hex[:12]; started=time.time()
    try:
        message=req.message.strip(); history=[x.model_dump() for x in req.history[-MAX_HISTORY:]]
        memories=memory.search(req.user_id,message) if memory.enabled() else []; memory_text="\n".join(f"- {m.get('content','')}" for m in memories[:6]); evidence=req.memory_context.strip(); sources=[]; low=message.lower()
        needs=req.deep_search or any(t in low for t in ["search","research","latest","current","compare","sources","look up","find out","today"])
        if needs:
            evidence2,sources2=remote_research(message)
            if evidence2 is None:evidence2,sources2=local_research.research(message,max_sources=8)
            evidence=(evidence+"\n\n"+evidence2).strip() if evidence and evidence2 else (evidence2 or evidence); sources.extend(sources2)
            for x in local_research.domain_tools(message):
                evidence+=("\n\n" if evidence else "")+f"[{x['source']}] {x['title']}\n{x['text']}"; sources.append(x)
        result=ai.answer(message,history,evidence,req.royal_mode,needs,memory_text); response=result.get("response")
        if response and needs and JUDGE_BACKEND_URL:
            audited=remote_judge({"request":message,"draft":response,"evidence":evidence[:12000],"royal_mode":req.royal_mode})
            if audited:response=audited;result["mode"]="audited-team"
        if not response:response="I received the request, but no configured AI provider returned an answer. Check the AI provider environment variables and logs."
        try:response=validator.validate_code_blocks(response)
        except Exception as e:print("[Validator]",e)
        if memory.enabled():
            memory.save_message(req.user_id,"user",message);memory.save_message(req.user_id,"assistant",response)
            if any(x in low for x in ["remember that","remember this","don't forget","do not forget","my goal is","my favorite is"]):memory.save(req.user_id,message,importance=5)
        return {"response":response,"mode":result.get("mode","unknown"),"providers":result.get("providers",[]),"sources_count":len(sources),"sources":[{"title":x.get("title","Source"),"url":x.get("url",""),"source":x.get("source","")} for x in sources[:8]],"researched":bool(needs),"memory_used":bool(memories),"request_id":rid,"elapsed_ms":round((time.time()-started)*1000)}
    except HTTPException:raise
    except Exception as e:
        print(f"[CHAT {rid}] {type(e).__name__}: {e}");raise HTTPException(500,"Internal Shadow AI error. Check Railway logs for the request ID.")
    finally:CHAT_SLOTS.release()
