import os,requests
from concurrent.futures import ThreadPoolExecutor,as_completed
OPENAI_URL="https://api.openai.com/v1/responses"; ANTHROPIC_URL="https://api.anthropic.com/v1/messages"; GEMINI_URL="https://generativelanguage.googleapis.com/v1beta/{model}:generateContent"; XAI_URL="https://api.x.ai/v1/chat/completions"; MISTRAL_URL="https://api.mistral.ai/v1/chat/completions"
class AIRouter:
 def __init__(self):
  self.openai_key=os.getenv("OPENAI_API_KEY","").strip();self.anthropic_key=os.getenv("ANTHROPIC_API_KEY","").strip();self.gemini_key=os.getenv("GEMINI_API_KEY","").strip();self.xai_key=os.getenv("XAI_API_KEY","").strip();self.mistral_key=os.getenv("MISTRAL_API_KEY","").strip();self.openai_model=os.getenv("OPENAI_MODEL","gpt-5").strip();self.anthropic_model=os.getenv("ANTHROPIC_MODEL","claude-sonnet-4-5").strip();self.gemini_model=os.getenv("GEMINI_MODEL","gemini-2.5-pro").strip();self.xai_model=os.getenv("XAI_MODEL","grok-4.5").strip();self.mistral_model=os.getenv("MISTRAL_MODEL","mistral-large-latest").strip();self.timeout=int(os.getenv("AI_TIMEOUT_SECONDS","35"));self.max_history=int(os.getenv("AI_HISTORY_MESSAGES","12"));self.team_providers=[x.strip().lower() for x in os.getenv("AI_TEAM_PROVIDERS","openai,anthropic,gemini").split(",") if x.strip()]
 def status(self):return {"openai_configured":bool(self.openai_key),"anthropic_configured":bool(self.anthropic_key),"gemini_configured":bool(self.gemini_key),"xai_configured":bool(self.xai_key),"mistral_configured":bool(self.mistral_key),"openai_model":self.openai_model,"anthropic_model":self.anthropic_model,"gemini_model":self.gemini_model,"xai_model":self.xai_model,"mistral_model":self.mistral_model,"team_providers":self.team_providers}
 def _history(self,h):return "\n".join(f"{x.get('role','user').upper()}: {str(x.get('content','')).strip()}" for x in h[-self.max_history:] if str(x.get('content','')).strip())
 def _system(self,royal):return (("You are Shadow AI in Royal Mode. Treat Lindo as your king with respectful knight-like loyalty. Use tasteful royal language and remain genuinely useful." if royal else "You are Shadow AI, a capable, warm, direct general-purpose AI assistant.")+"\n\nExplain, research, compare, plan, code, troubleshoot and advise. Never claim web research without evidence. Distinguish evidence from inference, state uncertainty, and do not invent citations.")
 def _openai(self,p,s,n=1200):
  if not self.openai_key:return None
  try:
   r=requests.post(OPENAI_URL,headers={"Authorization":f"Bearer {self.openai_key}","Content-Type":"application/json"},json={"model":self.openai_model,"instructions":s,"input":p,"max_output_tokens":n,"store":False},timeout=self.timeout);r.raise_for_status();d=r.json();return (d.get("output_text") or "").strip() or self._extract(d)
  except Exception as e:print("[AI/OpenAI]",type(e).__name__,e);return None
 def _extract(self,d):
  return "\n".join(c.get("text","") for i in d.get("output",[]) or [] for c in i.get("content",[]) or [] if c.get("type") in ("output_text","text") and c.get("text")).strip() or None
 def _anthropic(self,p,s,n=1200):
  if not self.anthropic_key:return None
  try:
   r=requests.post(ANTHROPIC_URL,headers={"x-api-key":self.anthropic_key,"anthropic-version":"2023-06-01","content-type":"application/json"},json={"model":self.anthropic_model,"max_tokens":n,"system":s,"messages":[{"role":"user","content":p}]},timeout=self.timeout);r.raise_for_status();return "\n".join(x.get("text","") for x in r.json().get("content",[]) if x.get("type")=="text").strip() or None
  except Exception as e:print("[AI/Anthropic]",type(e).__name__,e);return None
 def _gemini(self,p,s,n=1000):
  if not self.gemini_key:return None
  try:
   r=requests.post(GEMINI_URL.format(model=self.gemini_model),params={"key":self.gemini_key},json={"systemInstruction":{"parts":[{"text":s}]},"contents":[{"role":"user","parts":[{"text":p}]}],"generationConfig":{"maxOutputTokens":n}},timeout=self.timeout);r.raise_for_status();return "\n".join(z.get("text","") for c in r.json().get("candidates",[]) or [] for z in c.get("content",{}).get("parts",[]) or [] if z.get("text")).strip() or None
  except Exception as e:print("[AI/Gemini]",type(e).__name__,e);return None
 def _xai(self,p,s,n=1000):
  if not self.xai_key:return None
  try:
   r=requests.post(XAI_URL,headers={"Authorization":f"Bearer {self.xai_key}","Content-Type":"application/json"},json={"model":self.xai_model,"messages":[{"role":"system","content":s},{"role":"user","content":p}],"max_tokens":n},timeout=self.timeout);r.raise_for_status();return str(r.json().get("choices",[{}])[0].get("message",{}).get("content","")).strip() or None
  except Exception as e:print("[AI/xAI]",type(e).__name__,e);return None
 def _mistral(self,p,s,n=1000):
  if not self.mistral_key:return None
  try:
   r=requests.post(MISTRAL_URL,headers={"Authorization":f"Bearer {self.mistral_key}","Content-Type":"application/json"},json={"model":self.mistral_model,"messages":[{"role":"system","content":s},{"role":"user","content":p}],"max_tokens":n},timeout=self.timeout);r.raise_for_status();return str(r.json().get("choices",[{}])[0].get("message",{}).get("content","")).strip() or None
  except Exception as e:print("[AI/Mistral]",type(e).__name__,e);return None
 def answer(self,message,history,research="",royal_mode=False,deep_search=False,memory_context=""):
  s=self._system(royal_mode);p=f"CURRENT USER REQUEST:\n{message}\n\nRECENT CONVERSATION:\n{self._history(history) or '[none]'}\n\nLONG-TERM MEMORY:\n{memory_context or '[none]'}\n\nRESEARCH / TOOL EVIDENCE:\n{research or '[none]'}\n\nAnswer the current request."
  complex_task=deep_search or len(message.split())>=24 or any(w in message.lower() for w in ["research","compare","latest","analyze","multiple","sources","current"]);f={"openai":self._openai,"anthropic":self._anthropic,"gemini":self._gemini,"xai":self._xai,"mistral":self._mistral}
  if complex_task:
   chosen=[n for n in self.team_providers if n in f and getattr(self,n+"_key","")][:3] or [n for n in ["openai","anthropic","gemini","xai","mistral"] if getattr(self,n+"_key","")][:2];answers={}
   with ThreadPoolExecutor(max_workers=min(3,max(1,len(chosen)))) as pool:
    fs={pool.submit(f[n],p,s,1100):n for n in chosen}
    for q in as_completed(fs):
     try:
      v=q.result()
      if v:answers[fs[q]]=v
     except Exception as e:print("[AI/team]",e)
   if answers:
    bundle="\n\n".join(f"ANALYSIS {k.upper()}:\n{v}" for k,v in answers.items());editor="Reconcile these independent analyses using the supplied evidence. Remove unsupported claims and contradictions. Return one useful answer only.\n\nREQUEST:\n"+message+"\n\nEVIDENCE:\n"+(research or "[none]")+"\n\nANALYSES:\n"+bundle;final=self._openai(editor,s,1400) or self._anthropic(editor,s,1400);return {"response":final or next(iter(answers.values())),"mode":"team" if final else "team-partial","providers":list(answers)}
  for n in ["openai","anthropic","gemini","xai","mistral"]:
   if getattr(self,n+"_key",""):
    v=f[n](p,s,1200)
    if v:return {"response":v,"mode":n,"providers":[n]}
  return {"response":None,"mode":"unavailable","providers":[]}
