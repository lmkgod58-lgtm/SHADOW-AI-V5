import re,socket,ipaddress,requests
from urllib.parse import urlparse,urljoin
from bs4 import BeautifulSoup
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
app=FastAPI(title="Shadow AI Web Intelligence",version="1.1")
S=requests.Session();S.headers.update({"User-Agent":"ShadowAI-Web/1.1","Accept-Language":"en-US,en;q=0.8"})
class FetchRequest(BaseModel):url:str=Field(min_length=8,max_length=2000)
def safe_target(url):
 p=urlparse(url)
 if p.scheme not in {"http","https"} or not p.hostname:raise HTTPException(400,"Only public HTTP/HTTPS URLs are allowed")
 try:
  for info in socket.getaddrinfo(p.hostname,None):
   ip=ipaddress.ip_address(info[4][0])
   if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:raise HTTPException(400,"Private or local network targets are blocked")
 except socket.gaierror:raise HTTPException(400,"Host could not be resolved")
 return p
@app.get("/")
def root():return {"status":"web intelligence operational"}
@app.get("/health")
def health():return {"status":"ok"}
@app.post("/fetch")
def fetch(req:FetchRequest):
 p=safe_target(req.url)
 try:
  r=S.get(req.url,timeout=(5,12),allow_redirects=False);count=0
  while 300<=r.status_code<400 and count<3:
   location=r.headers.get("location")
   if not location:break
   target=urljoin(req.url,location);safe_target(target);r=S.get(target,timeout=(5,12),allow_redirects=False);count+=1
  r.raise_for_status();soup=BeautifulSoup(r.text,"html.parser")
  for t in soup(["script","style","noscript"]):t.decompose()
  text=re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
  return {"url":r.url,"domain":urlparse(r.url).netloc,"title":soup.title.get_text(" ",strip=True) if soup.title else urlparse(r.url).netloc,"text":text[:12000]}
 except HTTPException:raise
 except Exception as e:raise HTTPException(502,f"Fetch failed: {type(e).__name__}")
