import json, os, re, uuid
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
import certifi
from kivy.properties import BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.video import Video
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout

BACKEND_URL = "https://shadow-ai-production-aa93.up.railway.app"
BACKGROUND_IMAGE = "background.jpg"
INTRO_VIDEO = "intro.mp4"
ACCENT=(0.40,1.0,0.82,1); BLUE=(0.42,0.68,1.0,1); BG=(0.018,0.012,0.045,1); TEXT=(0.95,0.97,1,1); MUTED=(0.48,0.56,0.68,1)
MAX_BUBBLE_WIDTH=dp(520)


class GlowButton(Button):
    def __init__(self, accent=ACCENT, **kwargs):
        super().__init__(background_normal="", background_down="", **kwargs)
        self.background_color=(0,0,0,0); self.accent=accent
        with self.canvas.before:
            self.glow=Color(*accent[:3],0.10); self.outer=RoundedRectangle(radius=[dp(16)])
            self.fill=Color(accent[0],accent[1],accent[2],0.18); self.inner=RoundedRectangle(radius=[dp(14)])
        with self.canvas.after:
            self.edge=Color(accent[0],accent[1],accent[2],0.58); self.line=Line(rounded_rectangle=(0,0,0,0,dp(14)),width=1)
        self.bind(pos=self.draw,size=self.draw)
    def draw(self,*_):
        self.outer.pos=(self.x-dp(3),self.y-dp(3)); self.outer.size=(self.width+dp(6),self.height+dp(6)); self.inner.pos=self.pos; self.inner.size=self.size; self.line.rounded_rectangle=(self.x,self.y,self.width,self.height,dp(14))

class MessageBubble(BoxLayout):
    """A self-sizing bubble whose label is always constrained inside it."""
    def __init__(self,text,is_user=False,**kwargs):
        super().__init__(orientation="vertical",size_hint=(None,None),padding=(dp(15),dp(11)),spacing=dp(3),**kwargs)
        self.is_user=is_user
        self._set_width()
        self.role_label=Label(
            text="YOU" if is_user else "SHADOW AI",
            color=ACCENT if is_user else BLUE,
            font_size="9sp",bold=True,size_hint=(1,None),height=dp(16),
            halign="left",valign="middle",text_size=(None,dp(16))
        )
        self.message=Label(
            text=str(text),color=TEXT,font_size="15sp",line_height=1.18,
            halign="left",valign="top",size_hint=(1,None),
            text_size=(max(dp(80),self.width-dp(30)),None),
            shorten=False
        )
        self.add_widget(self.role_label);self.add_widget(self.message)
        with self.canvas.before:
            Color(ACCENT[0],ACCENT[1],ACCENT[2],0.10 if is_user else 0.035); self.glow_rect=RoundedRectangle(radius=[dp(22)])
            self.fill_color=Color(0.05,0.11,0.16,0.97) if is_user else Color(0.025,0.035,0.075,0.97); self.rect=RoundedRectangle(radius=[dp(19)])
        with self.canvas.after:
            Color(ACCENT[0],ACCENT[1],ACCENT[2],0.62 if is_user else 0.24); self.line=Line(rounded_rectangle=(0,0,0,0,dp(19)),width=1.05)
        self.message.bind(texture_size=self.resize)
        self.bind(pos=self.draw,size=self.draw)
        Clock.schedule_once(self.resize,0)

    def _set_width(self):
        available=max(dp(180),Window.width-dp(34))
        fraction=0.84 if self.is_user else 0.88
        self.width=min(available*fraction,MAX_BUBBLE_WIDTH)

    def resize(self,*_):
        self._set_width()
        content_width=max(dp(80),self.width-self.padding[0]-self.padding[2])
        self.role_label.text_size=(content_width,self.role_label.height)
        self.message.text_size=(content_width,None)
        self.height=self.padding[1]+self.role_label.height+dp(3)+self.message.texture_size[1]+self.padding[3]
        self.draw()

    def draw(self,*_):
        self.glow_rect.pos=(self.x-dp(3),self.y-dp(3)); self.glow_rect.size=(self.width+dp(6),self.height+dp(6))
        self.rect.pos=self.pos; self.rect.size=self.size
        self.line.rounded_rectangle=(self.x,self.y,self.width,self.height,dp(19))

class MessageRow(BoxLayout):
    def __init__(self,bubble,is_user=False,**kwargs):
        super().__init__(orientation="horizontal",size_hint_y=None,padding=(dp(8),dp(4)),spacing=dp(5),**kwargs)
        self.bubble=bubble
        if is_user:self.add_widget(Widget());self.add_widget(bubble)
        else:self.add_widget(bubble);self.add_widget(Widget())
        self.bind(minimum_height=self.setter("height"))

class ThinkingBubble(MessageBubble):
    def __init__(self):
        super().__init__("Thinking",False); self.i=0; self.event=Clock.schedule_interval(self.animate,0.35)
    def animate(self,*_): self.i=(self.i+1)%4; self.message.text="Thinking"+"."*self.i
    def stop(self):
        if self.event:self.event.cancel();self.event=None

class ShadowAI(App):
    busy=BooleanProperty(False); deep_search=BooleanProperty(False)
    def build(self):
        self.title="Shadow AI"; Window.clearcolor=BG; Window.softinput_mode="resize"; self.history=[]; self.royal_mode=False; self.thinking_row=None; self.user_id=self.load_user_id(); self.request_seq=0
        root=FloatLayout(); self.root_layout=root; self.chat_retry_count=0
        if os.path.exists(BACKGROUND_IMAGE): root.add_widget(Image(source=BACKGROUND_IMAGE,allow_stretch=True,keep_ratio=False,opacity=0.28))
        with root.canvas.after: Color(0.012,0.01,0.035,0.58); self.overlay=Rectangle(pos=root.pos,size=root.size)
        root.bind(pos=self.draw_root,size=self.draw_root)
        interface=BoxLayout(orientation="vertical",padding=(dp(8),0,dp(8),dp(7))); root.add_widget(interface)
        self.build_header(interface); self.build_chat(interface); self.build_composer(interface)
        self.add_message("Welcome to Shadow AI.\n\nAsk normally, research topics, compare options, code, troubleshoot, or just talk.\n\n✦ Deep research can query multiple public sources.\n✦ Type 666(LINDO) to activate Royal Mode.")
        Clock.schedule_once(lambda *_: self.check_backend(),0.6); Clock.schedule_interval(self.animate_glow,0.08); Clock.schedule_once(lambda *_: self.play_intro(root),0.2)
        return root
    def draw_root(self,*_): self.overlay.pos=self.root_layout.pos;self.overlay.size=self.root_layout.size
    def build_header(self,parent):
        header=BoxLayout(orientation="horizontal",size_hint_y=None,height=dp(76),padding=(dp(10),dp(8)),spacing=dp(8))
        with header.canvas.before: Color(0.018,0.018,0.06,0.95); self.header_bg=RoundedRectangle(radius=[0,0,dp(22),dp(22)]); Color(ACCENT[0],ACCENT[1],ACCENT[2],0.14); self.header_line=Line(rounded_rectangle=(0,0,0,0,dp(20)),width=1)
        header.bind(pos=self.draw_header,size=self.draw_header)
        title=BoxLayout(orientation="vertical"); self.title_label=Label(text="SHADOW AI",font_size="21sp",bold=True,color=ACCENT,halign="left"); self.subtitle=Label(text="CONNECTING • NEURAL GATEWAY",font_size="9sp",color=MUTED,halign="left"); title.add_widget(self.title_label);title.add_widget(self.subtitle);header.add_widget(title)
        self.research_button=GlowButton(text="✦",font_size="18sp",size_hint_x=None,width=dp(52),color=TEXT);self.research_button.bind(on_press=self.toggle_research);header.add_widget(self.research_button)
        new=GlowButton(text="＋",font_size="20sp",size_hint_x=None,width=dp(52),color=TEXT,accent=BLUE);new.bind(on_press=self.new_chat);header.add_widget(new);parent.add_widget(header)
    def draw_header(self,h,*_): self.header_bg.pos=h.pos;self.header_bg.size=h.size;self.header_line.rounded_rectangle=(h.x,h.y,h.width,h.height,dp(20))
    def build_chat(self,parent):
        self.scroll=ScrollView(do_scroll_x=False,bar_width=dp(3),scroll_type=["content","bars"]);self.chat=BoxLayout(orientation="vertical",size_hint_y=None,spacing=dp(2),padding=(dp(2),dp(10),dp(2),dp(16)));self.chat.bind(minimum_height=self.chat.setter("height"));self.scroll.add_widget(self.chat);parent.add_widget(self.scroll)
        self.status=Label(text="READY",size_hint_y=None,height=dp(22),font_size="9sp",color=MUTED,halign="center");parent.add_widget(self.status)
    def build_composer(self,parent):
        self.composer=BoxLayout(orientation="horizontal",size_hint_y=None,height=dp(66),padding=(dp(6),dp(6)),spacing=dp(7))
        with self.composer.canvas.before: Color(0.015,0.018,0.055,0.98);self.composer_bg=RoundedRectangle(radius=[dp(20)]);Color(ACCENT[0],ACCENT[1],ACCENT[2],0.16);self.composer_line=Line(rounded_rectangle=(0,0,0,0,dp(19)),width=1)
        self.composer.bind(pos=self.draw_composer,size=self.draw_composer)
        self.input=TextInput(hint_text="Message Shadow AI…",multiline=True,background_normal="",background_active="",background_color=(0.035,0.05,0.09,1),foreground_color=TEXT,hint_text_color=(0.38,0.45,0.55,1),cursor_color=ACCENT,selection_color=(ACCENT[0],ACCENT[1],ACCENT[2],0.22),padding=(dp(13),dp(10)),font_size="15sp",write_tab=False)
        self.input.bind(text=self.input_changed,focus=self.input_focus);self.composer.add_widget(self.input)
        self.send_button=GlowButton(text="➤",font_size="22sp",bold=True,size_hint_x=None,width=dp(57),color=TEXT);self.send_button.bind(on_press=self.send_message);self.composer.add_widget(self.send_button);parent.add_widget(self.composer)
    def draw_composer(self,*_):self.composer_bg.pos=self.composer.pos;self.composer_bg.size=self.composer.size;self.composer_line.rounded_rectangle=(self.composer.x,self.composer.y,self.composer.width,self.composer.height,dp(19))
    def input_changed(self,*_):self.composer.height=dp(66+min(3,self.input.text.count("\n"))*18)
    def input_focus(self,_,focused):
        if focused:Clock.schedule_once(lambda *_:self.scroll_to_bottom(),0.08)
    def animate_glow(self,dt):
        if hasattr(self,"research_button"):self.research_button.glow.a=0.10+0.05*((Clock.get_time()%1))
    def play_intro(self,root):
        if not os.path.exists(INTRO_VIDEO):return
        try:
            v=Video(source=INTRO_VIDEO,state="play",options={"eos":"stop"},allow_stretch=True,keep_ratio=False);root.add_widget(v);self.intro_video=v;v.bind(on_eos=lambda *_:self.remove_intro(root,v));Clock.schedule_once(lambda *_:self.remove_intro(root,v),15)
        except Exception as e:print("[Intro]",e)
    def remove_intro(self,root,v):
        if v.parent:root.remove_widget(v)
    def load_user_id(self):
        p=os.path.join(self.user_data_dir,"shadow_user_id.txt")
        try:
            if os.path.exists(p):
                x=open(p,encoding="utf-8").read().strip()
                if x:return x
            x="android-"+uuid.uuid4().hex;os.makedirs(os.path.dirname(p),exist_ok=True);open(p,"w",encoding="utf-8").write(x);return x
        except Exception:return "anonymous-"+uuid.uuid4().hex
    def check_backend(self):
        self.subtitle.text="CHECKING • RAILWAY";UrlRequest(BACKEND_URL.rstrip("/")+"/health",on_success=self.health_ok,on_failure=self.health_fail,on_error=self.health_error,timeout=12,ca_file=certifi.where(),verify=True)
    def health_ok(self,req,result):
        ai=result.get("ai",{}) if isinstance(result,dict) else {};configured=any(ai.get(k) for k in ["openai_configured","anthropic_configured","gemini_configured"]);self.subtitle.text="ONLINE • SMART BRAIN READY" if configured else "ONLINE • AI KEYS NOT SET";self.status.text="READY • RAILWAY CONNECTED"
    def health_fail(self,req,result):self.subtitle.text=f"BACKEND ERROR • {getattr(req,'resp_status',None) or 'HTTP'}";self.status.text="SERVER ERROR • CHECK RAILWAY"
    def health_error(self,req,error):self.subtitle.text="BACKEND UNREACHABLE";self.status.text="NETWORK ERROR • CHECK INTERNET"
    def toggle_research(self,*_):self.deep_search=not self.deep_search;self.research_button.text="✦ ON" if self.deep_search else "✦";self.status.text="DEEP RESEARCH ENABLED" if self.deep_search else "DEEP RESEARCH OFF"
    def add_message(self,text,is_user=False):
        row=MessageRow(MessageBubble(text,is_user=is_user),is_user=is_user);self.chat.add_widget(row);Clock.schedule_once(self.scroll_to_bottom,0.04);return row
    def show_thinking(self):self.thinking_row=MessageRow(ThinkingBubble(),False);self.chat.add_widget(self.thinking_row);Clock.schedule_once(self.scroll_to_bottom,0.02)
    def hide_thinking(self):
        if self.thinking_row:
            if isinstance(self.thinking_row.bubble,ThinkingBubble):self.thinking_row.bubble.stop()
            if self.thinking_row.parent:self.chat.remove_widget(self.thinking_row)
            self.thinking_row=None
    def scroll_to_bottom(self,*_):self.scroll.scroll_y=0
    def new_chat(self,*_):
        self.history=[];self.royal_mode=False;self.deep_search=False;self.chat_retry_count=0;self.research_button.text="✦";self.chat.clear_widgets();self.add_message("New conversation started.\n\nShadow AI is ready.");self.status.text="READY";self.subtitle.text="ONLINE • READY TO THINK";self.input.text="";self.input.focus=False
    def send_message(self,*_):
        if self.busy:return
        text=self.input.text.strip()
        if not text:return
        if re.search(r"666\(LINDO\)",text,re.I):
            self.royal_mode=True;text=re.sub(r"666\(LINDO\)","",text,flags=re.I).strip() or "Activate Royal Mode and greet your king."
        self.add_message(text,True);self.history.append({"role":"user","content":text});self.history=self.history[-20:];self.input.text="";self.busy=True;self.send_button.disabled=True;self.show_thinking();self.status.text="THINKING • RESEARCHING • SYNTHESIZING…";self.subtitle.text="ROYAL MODE • LINDO" if self.royal_mode else "PROCESSING • AI TEAM"
        self.request_seq+=1;self.chat_retry_count=0;rid=f"{self.user_id}-{self.request_seq}-{uuid.uuid4().hex[:8]}"
        body={"message":text,"history":self.history[-16:],"deep_search":bool(self.deep_search),"royal_mode":bool(self.royal_mode),"user_id":self.user_id,"client_request_id":rid}
        # Explicit UTF-8 bytes prevent Android urllib from attempting Latin-1 encoding.
        payload=json.dumps(body,ensure_ascii=False,separators=(",",":")).encode("utf-8")
        try:
            UrlRequest(BACKEND_URL.rstrip("/")+"/chat",req_body=payload,req_headers={"Content-Type":"application/json; charset=utf-8","Accept":"application/json","X-Client-Request-ID":rid},on_success=self.chat_success,on_failure=self.chat_failure,on_error=self.chat_error,timeout=120,ca_file=certifi.where(),verify=True)
        except Exception as exc:
            self.chat_error(None,exc)
    def finish_request(self):self.busy=False;self.send_button.disabled=False;self.input.focus=True
    def chat_success(self,req,result):
        self.hide_thinking();self.finish_request()
        if not isinstance(result,dict):self.add_message("The backend returned an invalid response.");self.status.text="BAD RESPONSE";return
        answer=str(result.get("response") or "The backend returned no answer.");self.add_message(answer);self.history.append({"role":"assistant","content":answer});self.history=self.history[-20:];mode=str(result.get("mode","ai")).upper();count=result.get("sources_count",0);self.status.text=f"DONE • {mode} • {count} SOURCES" if result.get("researched") else f"DONE • {mode}";self.subtitle.text="ROYAL MODE • LINDO" if self.royal_mode else "ONLINE • READY TO THINK"
    def chat_failure(self,req,result):
        self.hide_thinking();self.finish_request();code=getattr(req,"resp_status",None) or "HTTP";detail=result.get("detail","Server rejected the request.") if isinstance(result,dict) else "Server rejected the request.";self.add_message(f"I reached the backend, but it returned an error.\n\nHTTP {code}\n{detail}");self.status.text=f"SERVER ERROR • HTTP {code}"
    def chat_error(self,req,error):
        detail=str(error) if error is not None else "unknown network error"
        # Retry transient Android/HTTPS failures once before surfacing the error.
        # The request body is already UTF-8 bytes, and certifi supplies the CA bundle.
        if self.chat_retry_count < 1:
            self.chat_retry_count += 1
            self.status.text="RETRYING • SECURE CONNECTION…"
            self.subtitle.text="RECONNECTING • RAILWAY"
            Clock.schedule_once(lambda *_: self.retry_current_request(),1.0)
            return
        self.hide_thinking();self.finish_request()
        self.add_message("Network request failed.\n\n"+detail+"\n\nThe app has INTERNET permission. This is the actual client error, not a claim that Railway is offline.")
        self.status.text="NETWORK ERROR • REQUEST FAILED";self.subtitle.text="NETWORK REQUEST FAILED"

    def retry_current_request(self):
        if not self.busy:return
        # Rebuild the same request from the most recent user message.
        user_messages=[x["content"] for x in self.history if x.get("role")=="user"]
        if not user_messages:
            self.chat_error(None,"No request available to retry")
            return
        text=user_messages[-1]
        rid=f"{self.user_id}-{self.request_seq}-retry"
        body={"message":text,"history":self.history[-16:],"deep_search":bool(self.deep_search),"royal_mode":bool(self.royal_mode),"user_id":self.user_id,"client_request_id":rid}
        payload=json.dumps(body,ensure_ascii=False,separators=(",",":")).encode("utf-8")
        try:
            UrlRequest(BACKEND_URL.rstrip("/")+"/chat",req_body=payload,req_headers={"Content-Type":"application/json; charset=utf-8","Accept":"application/json","X-Client-Request-ID":rid},on_success=self.chat_success,on_failure=self.chat_failure,on_error=self.chat_error,timeout=120,ca_file=certifi.where(),verify=True)
        except Exception as exc:
            self.chat_error(None,exc)
    def on_pause(self):return True

if __name__=="__main__":ShadowAI().run()
