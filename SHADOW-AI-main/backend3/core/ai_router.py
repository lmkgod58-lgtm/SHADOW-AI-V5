import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

OPENAI_URL = "https://api.openai.com/v1/responses"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/{model}:generateContent"
XAI_URL = "https://api.x.ai/v1/chat/completions"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


class AIRouter:
    """Direct provider router. No OpenAI-compatible proxy is used."""

    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.xai_key = os.getenv("XAI_API_KEY", "").strip()
        self.mistral_key = os.getenv("MISTRAL_API_KEY", "").strip()
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5").strip()
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro").strip()
        self.xai_model = os.getenv("XAI_MODEL", "grok-4.5").strip()
        self.mistral_model = os.getenv("MISTRAL_MODEL", "mistral-large-latest").strip()
        self.timeout = int(os.getenv("AI_TIMEOUT_SECONDS", "45"))
        self.max_history = int(os.getenv("AI_HISTORY_MESSAGES", "16"))

    def status(self) -> Dict[str, Any]:
        return {
            "openai_configured": bool(self.openai_key),
            "anthropic_configured": bool(self.anthropic_key),
            "gemini_configured": bool(self.gemini_key),
            "xai_configured": bool(self.xai_key),
            "mistral_configured": bool(self.mistral_key),
            "openai_model": self.openai_model,
            "anthropic_model": self.anthropic_model,
            "gemini_model": self.gemini_model,
            "xai_model": self.xai_model,
            "mistral_model": self.mistral_model,
        }

    def _history_text(self, history: List[Dict[str, str]]) -> str:
        lines = []
        for item in history[-self.max_history:]:
            content = str(item.get("content", "")).strip()
            if content:
                lines.append(f"{item.get('role', 'user').upper()}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _system(royal_mode: bool) -> str:
        identity = (
            "You are Shadow AI in Royal Mode. Treat Lindo as your king with respectful knight-like loyalty. "
            "Use tasteful royal language, call him Lindo or my king naturally, and remain genuinely useful."
            if royal_mode else
            "You are Shadow AI, a capable, warm, direct general-purpose AI assistant."
        )
        return identity + "\n\n" + (
            "You can explain, research, compare, plan, code, troubleshoot and advise. "
            "Never claim to have searched the web unless evidence is supplied. "
            "When evidence is supplied, distinguish facts from inference, reconcile conflicts, and state uncertainty. "
            "Do not invent citations or URLs. Use the user's recent context without pretending to remember unavailable details. "
            "For coding, provide runnable code and preserve existing project constraints unless a change is necessary."
        )

    def _openai(self, prompt: str, system: str, max_output_tokens: int = 1200) -> Optional[str]:
        if not self.openai_key:
            return None
        try:
            r = requests.post(OPENAI_URL, headers={"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}, json={
                "model": self.openai_model, "instructions": system, "input": prompt, "max_output_tokens": max_output_tokens
            }, timeout=self.timeout)
            r.raise_for_status(); data = r.json()
            if data.get("output_text"):
                return data["output_text"].strip()
            parts = []
            for item in data.get("output", []) or []:
                for c in item.get("content", []) or []:
                    if c.get("type") in ("output_text", "text") and c.get("text"):
                        parts.append(c["text"])
            return "\n".join(parts).strip() or None
        except Exception as exc:
            print(f"[AI/OpenAI] {type(exc).__name__}: {exc}")
            return None

    def _anthropic(self, prompt: str, system: str, max_tokens: int = 1200) -> Optional[str]:
        if not self.anthropic_key:
            return None
        try:
            r = requests.post(ANTHROPIC_URL, headers={"x-api-key": self.anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}, json={
                "model": self.anthropic_model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": prompt}]
            }, timeout=self.timeout)
            r.raise_for_status(); data = r.json()
            return "\n".join(x.get("text", "") for x in data.get("content", []) if x.get("type") == "text").strip() or None
        except Exception as exc:
            print(f"[AI/Anthropic] {type(exc).__name__}: {exc}")
            return None

    def _gemini(self, prompt: str, system: str, max_tokens: int = 1000) -> Optional[str]:
        if not self.gemini_key:
            return None
        try:
            url = GEMINI_URL.format(model=self.gemini_model)
            r = requests.post(url, params={"key": self.gemini_key}, json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens}
            }, timeout=self.timeout)
            r.raise_for_status(); data = r.json()
            parts = []
            for cand in data.get("candidates", []) or []:
                for p in cand.get("content", {}).get("parts", []) or []:
                    if p.get("text"): parts.append(p["text"])
            return "\n".join(parts).strip() or None
        except Exception as exc:
            print(f"[AI/Gemini] {type(exc).__name__}: {exc}")
            return None

    def _xai(self, prompt: str, system: str, max_tokens: int = 1000) -> Optional[str]:
        if not self.xai_key:
            return None
        try:
            r = requests.post(XAI_URL, headers={"Authorization": f"Bearer {self.xai_key}", "Content-Type": "application/json"}, json={
                "model": self.xai_model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "max_tokens": max_tokens
            }, timeout=self.timeout)
            r.raise_for_status(); data = r.json()
            return str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip() or None
        except Exception as exc:
            print(f"[AI/xAI] {type(exc).__name__}: {exc}")
            return None

    def _mistral(self, prompt: str, system: str, max_tokens: int = 1000) -> Optional[str]:
        if not self.mistral_key:
            return None
        try:
            r = requests.post(MISTRAL_URL, headers={"Authorization": f"Bearer {self.mistral_key}", "Content-Type": "application/json"}, json={
                "model": self.mistral_model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "max_tokens": max_tokens
            }, timeout=self.timeout)
            r.raise_for_status(); data = r.json()
            return str(data.get("choices", [{}])[0].get("message", {}).get("content", "")).strip() or None
        except Exception as exc:
            print(f"[AI/Mistral] {type(exc).__name__}: {exc}")
            return None

    def answer(self, message: str, history: List[Dict[str, str]], research: str = "", royal_mode: bool = False, deep_search: bool = False, memory_context: str = "") -> Dict[str, Any]:
        system = self._system(royal_mode)
        prompt = (
            f"CURRENT USER REQUEST:\n{message}\n\nRECENT CONVERSATION:\n{self._history_text(history) or '[none]'}\n\n"
            f"LONG-TERM MEMORY:\n{memory_context or '[none]'}\n\nRESEARCH / TOOL EVIDENCE:\n{research or '[none]'}\n\n"
            "Answer the current request. Use evidence when relevant and do not mention internal orchestration."
        )
        complex_task = deep_search or len(message.split()) >= 24 or any(w in message.lower() for w in ["research", "compare", "latest", "analyze", "multiple", "sources", "current"])
        if complex_task:
            providers = [
                ("openai", self._openai), ("anthropic", self._anthropic),
                ("gemini", self._gemini), ("xai", self._xai), ("mistral", self._mistral)
            ]
            # Primary pair are asked for drafts. The three optional critics are used only for complex work.
            with ThreadPoolExecutor(max_workers=5) as pool:
                futures = {pool.submit(fn, prompt, system, 1100): name for name, fn in providers}
                answers = {}
                for f in as_completed(futures):
                    name = futures[f]
                    try:
                        value = f.result()
                        if value: answers[name] = value
                    except Exception as exc:
                        print(f"[AI/{name}] worker error: {exc}")
            if answers:
                bundle = "\n\n".join(f"{k.upper()} ANALYSIS:\n{v}" for k, v in answers.items())
                judge_prompt = (
                    "You are the final editor. Multiple independent AI systems analyzed the same request. "
                    "Select only claims supported by the supplied evidence or solid reasoning. Identify contradictions, "
                    "discard weak guesses, and produce one coherent answer. Do not mention the models.\n\n"
                    f"REQUEST:\n{message}\n\nEVIDENCE:\n{research or '[none]'}\n\nANALYSES:\n{bundle}"
                )
                final = self._openai(judge_prompt, system, 1500) or self._anthropic(judge_prompt, system, 1500)
                if final:
                    return {"response": final, "mode": "team", "providers": list(answers)}
        # Fast path for simple chats.
        for name, fn in [("openai", self._openai), ("anthropic", self._anthropic), ("gemini", self._gemini)]:
            result = fn(prompt, system, 1200)
            if result:
                return {"response": result, "mode": name, "providers": [name]}
        return {"response": None, "mode": "unavailable", "providers": [], "error": "No configured AI provider returned a response."}
