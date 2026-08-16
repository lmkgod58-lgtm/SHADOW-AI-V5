import html, re, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple
from urllib.parse import quote_plus, urlparse
import requests
from bs4 import BeautifulSoup

class ResearchEngine:
    """Bounded multi-source research. It never executes arbitrary user commands."""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ShadowAI/4.0 research", "Accept-Language": "en-US,en;q=0.8"})

    def terminal_status(self):
        tools = {}
        for cmd in ["curl", "wget", "dig", "host", "whois", "python3"]:
            try:
                subprocess.run([cmd, "--version"], capture_output=True, timeout=2)
                tools[cmd] = True
            except Exception:
                tools[cmd] = False
        return tools

    def research(self, query: str, max_sources: int = 10) -> Tuple[str, List[Dict[str, str]]]:
        jobs = {
            "DuckDuckGo": lambda: self._duckduckgo(query),
            "Wikipedia": lambda: self._wikipedia(query),
            "GitHub": lambda: self._github(query),
            "ArXiv": lambda: self._arxiv(query),
        }
        q = query.lower()
        if any(x in q for x in ["python", "programming", "api", "javascript", "code"]):
            jobs["Python Docs"] = lambda: self._duckduckgo(f"site:docs.python.org {query}")[:3]
        if any(x in q for x in ["security", "vulnerability", "xss", "owasp", "cve", "cyber"]):
            jobs["OWASP"] = lambda: self._page("https://owasp.org/www-project-top-ten/")
        results=[]
        with ThreadPoolExecutor(max_workers=min(6, len(jobs))) as pool:
            futures={pool.submit(fn): name for name, fn in jobs.items()}
            for future in as_completed(futures):
                try:
                    for item in future.result() or []:
                        if item.get("text"): results.append(item)
                except Exception as exc:
                    print(f"[Research/{futures[future]}] {type(exc).__name__}: {exc}")
        unique=[]; seen=set()
        for item in results:
            key=(item.get("url","") or item.get("title","")).lower()
            if key in seen: continue
            seen.add(key); unique.append(item)
            if len(unique)>=max_sources: break
        evidence=[]
        for i,item in enumerate(unique,1):
            evidence.append(f"[{i}] {item.get('title','Source')}\nURL: {item.get('url','')}\n{item.get('text','')[:1800]}")
        return "\n\n".join(evidence), unique

    def domain_tools(self, query: str):
        domain=self._extract_domain(query)
        if not domain: return []
        out=[]
        for label,cmd in [("DNS",["dig","+short",domain]),("WHOIS",["whois",domain])]:
            try:
                p=subprocess.run(cmd,capture_output=True,text=True,timeout=8)
                text=(p.stdout or p.stderr).strip()
                if label=="WHOIS":
                    text="\n".join(x for x in text.splitlines() if any(k in x.lower() for k in ["registrar","name server","creation","expiration","country"]))
                if text: out.append({"source":label,"title":f"{label} for {domain}","url":domain,"text":text[:2000]})
            except Exception: pass
        return out

    def _duckduckgo(self,q):
        r=self.session.get(f"https://html.duckduckgo.com/html/?q={quote_plus(q)}",timeout=12); r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser"); out=[]
        for result in soup.select(".result")[:6]:
            a=result.select_one(".result__a"); s=result.select_one(".result__snippet")
            if a: out.append({"source":"DuckDuckGo","title":html.unescape(a.get_text(" ",strip=True)),"url":a.get("href",""),"text":html.unescape(s.get_text(" ",strip=True) if s else "")})
        return out
    def _wikipedia(self,q):
        r=self.session.get("https://en.wikipedia.org/w/api.php",params={"action":"query","list":"search","srsearch":q,"format":"json","srlimit":4},timeout=10); r.raise_for_status(); out=[]
        for x in r.json().get("query",{}).get("search",[]): out.append({"source":"Wikipedia","title":x.get("title","Wikipedia"),"url":"https://en.wikipedia.org/wiki/"+x.get("title","").replace(" ","_"),"text":BeautifulSoup(x.get("snippet",""),"html.parser").get_text(" ",strip=True)})
        return out
    def _github(self,q):
        r=self.session.get("https://api.github.com/search/repositories",params={"q":q,"per_page":4},timeout=10)
        if r.status_code>=400:return []
        return [{"source":"GitHub","title":x.get("full_name","GitHub"),"url":x.get("html_url",""),"text":x.get("description") or "No description."} for x in r.json().get("items",[])]
    def _arxiv(self,q):
        r=self.session.get("https://export.arxiv.org/api/query",params={"search_query":f"all:{q}","start":0,"max_results":4},timeout=12); r.raise_for_status()
        soup=BeautifulSoup(r.text,"xml"); out=[]
        for e in soup.find_all("entry"):
            out.append({"source":"arXiv","title":e.title.get_text(" ",strip=True) if e.title else "arXiv","url":e.id.get_text(strip=True) if e.id else "","text":e.summary.get_text(" ",strip=True)[:1800] if e.summary else ""})
        return out
    def _page(self,url):
        text=self._fetch_text(url); return [{"source":urlparse(url).netloc,"title":urlparse(url).netloc,"url":url,"text":text[:2200]}] if text else []
    def _fetch_text(self,url):
        try:
            r=self.session.get(url,timeout=12); r.raise_for_status(); soup=BeautifulSoup(r.text,"html.parser")
            for tag in soup(["script","style","noscript"]): tag.decompose()
            return re.sub(r"\s+"," ",soup.get_text(" ",strip=True))
        except Exception:return ""
    @staticmethod
    def _extract_domain(text):
        m=re.search(r"(?:https?://)?([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z0-9.-]+)",text)
        return m.group(1).strip(".,;:!?/") if m else None
