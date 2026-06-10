#!/usr/bin/env python3
"""
AI Token Monitor — 固定左上角桌面悬浮窗
左键 = 记录撞限 / 再点清除   右键 = 改重置时长
"""

import tkinter as tk
import json, time, threading, os
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

STATE    = Path.home() / 'token-monitor' / 'state.json'
KEY_FILE = Path.home() / '.config' / '.ai_monitor_keys'
PIN_MARGIN_X, PIN_MARGIN_Y = 30, 60  # distance from bottom-right edge

SERVICES = [
    {'name': 'Claude', 'color': '#E8885A', 'reset_h': 5  },
    {'name': 'Gemini', 'color': '#4A90D9', 'reset_h': 24 },
    {'name': 'Codex',  'color': '#10A37F', 'reset_h': 24 },
    {'name': 'Grok',   'color': '#26A7DE', 'reset_h': 24 },
    {'name': 'Kimi',   'color': '#FF7043', 'reset_h': 24 },
    {'name': 'Kilo',   'color': '#AB47BC', 'reset_h': 24 },
]

BG, BG2  = '#0d0d1e', '#13132a'
TBAR     = '#08081a'
FG       = '#c0c0e0'
OK       = '#22cc66'
WARN     = '#ff4455'
ORANGE   = '#ff8844'


def load_state():
    try:    return json.loads(STATE.read_text())
    except: return {}

def save_state(d):
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(d, indent=2))

def load_keys():
    try:    return json.loads(KEY_FILE.read_text())
    except: return {}


# ── 后台 API 获取器 ────────────────────────────────────────────
class APIFetcher:
    INTERVAL = 60  # 每60秒刷新一次

    def __init__(self):
        self.keys    = load_keys()
        self.api_data = {}   # name -> {label, pct, color, ok}
        self._lock   = threading.Lock()
        self._init_static()
        if HAS_REQUESTS:
            t = threading.Thread(target=self._loop, daemon=True)
            t.start()

    def _init_static(self):
        # Grok 已知 credits 耗尽
        with self._lock:
            self.api_data['Grok'] = {
                'label': 'Credits耗尽', 'pct': 0.0,
                'color': WARN, 'ok': False
            }

    def get(self, name):
        with self._lock:
            return self.api_data.get(name)

    def _loop(self):
        while True:
            self._fetch_kimi()
            self._fetch_gemini()
            self._fetch_claude()
            time.sleep(self.INTERVAL)

    def _fetch_kimi(self):
        key = self.keys.get('kimi')
        if not key:
            return
        try:
            r = requests.get(
                'https://api.moonshot.cn/v1/users/me',
                headers={'Authorization': f'Bearer {key}'},
                timeout=8
            )
            if r.status_code == 200:
                org   = r.json()['data']['organization']
                quota = org.get('max_token_quota', 0)
                used  = r.json()['data'].get(
                    'organization_usage', {}).get('total_tokens', 0)
                remain = quota - used
                pct   = remain / quota if quota else 1.0
                if remain >= 1_000_000:
                    lbl = f'{remain/1_000_000:.1f}M剩'
                elif remain >= 1000:
                    lbl = f'{remain//1000}K剩'
                else:
                    lbl = f'{remain}剩'
                with self._lock:
                    self.api_data['Kimi'] = {
                        'label': lbl, 'pct': pct,
                        'color': OK if pct > 0.2 else WARN, 'ok': True
                    }
        except Exception:
            pass

    def _fetch_gemini(self):
        key = self.keys.get('gemini')
        if not key:
            return
        try:
            r = requests.get(
                f'https://generativelanguage.googleapis.com/v1beta/models?key={key}',
                timeout=8
            )
            ok = r.status_code == 200
            with self._lock:
                self.api_data['Gemini'] = {
                    'label': 'Key ✓' if ok else 'Key无效',
                    'pct': 1.0 if ok else 0.0,
                    'color': OK if ok else WARN, 'ok': ok,
                    'show_countdown': True
                }
        except Exception:
            pass

    def _fetch_claude(self):
        key = self.keys.get('claude')
        org = self.keys.get('claude_org', '')
        if not key:
            return
        try:
            r = requests.get(
                'https://api.anthropic.com/v1/models',
                headers={
                    'x-api-key': key,
                    'anthropic-version': '2023-06-01',
                    'anthropic-organization': org,
                },
                timeout=8
            )
            ok = r.status_code == 200
            # 从响应头读取 rate limit 剩余
            rl_remaining = r.headers.get('anthropic-ratelimit-requests-remaining', '')
            rl_reset     = r.headers.get('anthropic-ratelimit-requests-reset', '')
            if ok and rl_remaining:
                lbl = f'RL:{rl_remaining}剩'
            elif ok:
                lbl = 'Key ✓'
            else:
                lbl = 'Key无效'
            with self._lock:
                self.api_data['Claude'] = {
                    'label': lbl, 'pct': 1.0 if ok else 0.0,
                    'color': OK if ok else WARN, 'ok': ok,
                    'show_countdown': True
                }
        except Exception:
            pass


# ── 主界面 ────────────────────────────────────────────────────
class App:
    def __init__(self):
        self.state   = load_state()
        self.fetcher = APIFetcher()
        self.root    = tk.Tk()
        self._setup_window()
        self._build_ui()
        self._update()
        self.root.mainloop()

    def _setup_window(self):
        r = self.root
        r.title('AI Tokens')
        r.configure(bg=BG)
        r.overrideredirect(True)
        r.attributes('-alpha', 0.92)
        r.resizable(False, False)

    def _calc_pos(self):
        r = self.root
        r.update_idletasks()
        sw = r.winfo_screenwidth()
        ww = r.winfo_width()
        x = sw - ww - PIN_MARGIN_X
        y = PIN_MARGIN_Y
        return x, y

    def _pin(self):
        x, y = self._calc_pos()
        self.root.geometry(f'+{x}+{y}')
        self.root.lift()
        self.root.after(5000, self._pin)

    def _build_ui(self):
        r = self.root
        bar = tk.Frame(r, bg=TBAR, height=18)
        bar.pack(fill='x')
        tk.Label(bar, text='  🤖 AI TOKENS', bg=TBAR, fg='#4455aa',
                 font=('Courier', 7, 'bold')).pack(side='left', pady=2)

        self.rows = {}
        for i, svc in enumerate(SERVICES):
            bg = BG if i % 2 == 0 else BG2
            f  = tk.Frame(r, bg=bg, padx=4, pady=2)
            f.pack(fill='x')

            dot = tk.Label(f, text='●', bg=bg, fg=OK, font=('Courier', 9))
            dot.pack(side='left')

            lbl = tk.Label(f, text=f" {svc['name']:<7}", bg=bg, fg=FG,
                           font=('Courier', 8, 'bold'), cursor='hand2')
            lbl.pack(side='left')

            cv = tk.Canvas(f, width=68, height=7, bg='#1a1a30',
                           highlightthickness=1, highlightbackground='#222244')
            cv.pack(side='left', padx=3)

            info = tk.Label(f, text='', bg=bg, fg=WARN,
                            font=('Courier', 7), width=12, anchor='w')
            info.pack(side='left')

            self.rows[svc['name']] = {'dot': dot, 'canvas': cv, 'info': info}

            for w in [f, dot, lbl, cv, info]:
                w.bind('<Button-1>', lambda e, n=svc['name']: self._toggle(n))
                w.bind('<Button-3>', lambda e, n=svc['name']: self._edit_hours(e, n))

        self.root.after(100, self._pin)

    # ── 手动撞限记录 ──────────────────────────────────────────
    def _toggle(self, name):
        now  = time.time()
        st   = self.state.setdefault(name, {})
        svc  = next(s for s in SERVICES if s['name'] == name)
        rsec = st.get('reset_h', svc['reset_h']) * 3600
        lat  = st.get('limited_at', 0)
        if lat and (now - lat) < rsec:
            st['limited_at'] = 0
        else:
            st['limited_at'] = now
        save_state(self.state)

    def _edit_hours(self, event, name):
        svc = next(s for s in SERVICES if s['name'] == name)
        st  = self.state.setdefault(name, {})
        cur = st.get('reset_h', svc['reset_h'])

        pop = tk.Toplevel(self.root)
        pop.configure(bg=BG)
        pop.attributes('-topmost', True)
        pop.overrideredirect(True)
        pop.geometry(f'+{event.x_root+10}+{event.y_root}')

        tk.Label(pop, text=f' {name} 重置(小时) ', bg=TBAR, fg=FG,
                 font=('Courier', 8)).pack(fill='x')
        var = tk.StringVar(value=str(cur))
        e   = tk.Entry(pop, textvariable=var, bg='#1a1a2e', fg=FG,
                       insertbackground=FG, font=('Courier', 10),
                       width=6, justify='center')
        e.pack(padx=8, pady=4)
        e.select_range(0, 'end')
        e.focus_set()

        def confirm(*_):
            try:
                st['reset_h'] = float(var.get())
                save_state(self.state)
            except ValueError:
                pass
            pop.destroy()

        tk.Button(pop, text=' 确定 ', command=confirm, bg='#222244', fg=FG,
                  font=('Courier', 8), relief='flat').pack(pady=(0, 6))
        e.bind('<Return>', confirm)
        pop.bind('<Escape>', lambda _: pop.destroy())

    # ── 每秒刷新显示 ─────────────────────────────────────────
    @staticmethod
    def _next_daily_reset(now):
        local = now + 8 * 3600
        return (int(local) // 86400 + 1) * 86400 - local

    def _update(self):
        now = time.time()
        for svc in SERVICES:
            name = svc['name']
            w    = self.rows[name]
            st   = self.state.get(name, {})
            rsec = st.get('reset_h', svc['reset_h']) * 3600
            lat  = st.get('limited_at', 0)
            rem  = max(0.0, (lat + rsec) - now) if lat else 0.0

            cv = w['canvas']
            cv.delete('all')

            # ── 优先显示 API 真实数据 ──────────────────────
            api = self.fetcher.get(name)

            if rem > 0:
                # 手动记录的撞限倒计时（优先级最高）
                pct = 1.0 - rem / rsec
                w['dot'].config(fg=WARN)
                h, m, s = int(rem//3600), int(rem%3600//60), int(rem%60)
                w['info'].config(text=f'{h}:{m:02d}:{s:02d}', fg='#ff4455')
                cv.create_rectangle(0, 0, 68, 7, fill='#2a0a0a', outline='')
                cv.create_rectangle(0, 0, max(2, int(68*pct)), 7, fill=WARN, outline='')

            elif api and not api['ok']:
                # API 返回无效/耗尽
                w['dot'].config(fg=WARN)
                w['info'].config(text=api['label'], fg=WARN)
                cv.create_rectangle(0, 0, 68, 7, fill='#2a0a0a', outline='')
                cv.create_rectangle(0, 0, 4, 7, fill=WARN, outline='')

            elif api and api['ok'] and not api.get('show_countdown'):
                # API 真实配额数据（Kimi）
                pct = api['pct']
                w['dot'].config(fg=api['color'])
                w['info'].config(text=api['label'], fg=api['color'])
                cv.create_rectangle(0, 0, 68, 7, fill='#1a1a0a', outline='')
                cv.create_rectangle(0, 0, max(2, int(68*pct)), 7,
                                    fill=api['color'], outline='')

            else:
                # 默认：倒计时到每日重置（UTC+8 午夜）
                daily = self._next_daily_reset(now)
                h, m, s = int(daily//3600), int(daily%3600//60), int(daily%60)
                dot_c  = api['color'] if api else OK
                prefix = (api['label'] + ' ') if (api and api.get('ok') and api.get('show_countdown')) else ''
                w['dot'].config(fg=dot_c)
                w['info'].config(text=f'{prefix}{h}:{m:02d}:{s:02d}', fg='#ff4444')
                pct = 1.0 - daily / 86400
                cv.create_rectangle(0, 0, 68, 7, fill='#0a1a0a', outline='')
                cv.create_rectangle(0, 0, max(2, int(68*pct)), 7,
                                    fill=svc['color'], outline='')

        self.root.after(1000, self._update)


if __name__ == '__main__':
    App()
