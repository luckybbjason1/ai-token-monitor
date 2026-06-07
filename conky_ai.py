#!/usr/bin/env python3
"""Conky AI token section — 血条 + 真实数据"""

import json, time
from pathlib import Path

STATE = Path.home() / 'token-monitor' / 'state.json'
CACHE = Path.home() / 'token-monitor' / 'api_cache.json'

SERVICES = [
    {'name': 'Claude', 'reset_h': 5 },
    {'name': 'Gemini', 'reset_h': 24},
    {'name': 'Codex',  'reset_h': 24},
    {'name': 'Grok',   'reset_h': 24},
    {'name': 'Kimi',   'reset_h': 24},
    {'name': 'Kilo',   'reset_h': 24},
]

def load(p):
    try:    return json.loads(Path(p).read_text())
    except Exception: return {}

def next_midnight(_now):
    from datetime import datetime, timedelta
    now_dt   = datetime.now()
    midnight = (now_dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (midnight - now_dt).total_seconds()

def fmt_cd(sec):
    h, m, s = int(sec//3600), int(sec%3600//60), int(sec%60)
    return f'{h}:{m:02d}:{s:02d}'

def bar(pct, width=9):
    """血条: pct=None → 无数据, 0~1 → 填充量"""
    if pct is None:
        return '${color 2A3550}' + '─' * width + '${color}'
    filled = round(pct * width)
    empty  = width - filled
    if   pct > 0.5: c = '50FA7B'   # 绿
    elif pct > 0.2: c = 'FFB86C'   # 橙
    else:           c = 'FF5555'   # 红
    b  = f'${{color {c}}}' + '█' * filled + '${color}'
    b += ('${color 2A3550}' + '░' * empty + '${color}') if empty else ''
    return b

state = load(STATE)
cache = load(CACHE)
now   = time.time()

lines = []
lines.append('${color 2A3550}${hr 1}${color}')
lines.append('${voffset 2}${color FFD700}AI TOKENS${color}')

for svc in SERVICES:
    name = svc['name']
    st   = state.get(name, {})
    rsec = st.get('reset_h', svc['reset_h']) * 3600
    lat  = st.get('limited_at', 0)
    rem  = max(0.0, (lat + rsec) - now) if lat else 0.0
    api  = cache.get(name, {})

    # ── 状态和百分比 ─────────────────────────────────────
    if rem > 0:
        # 手动记录的撞限倒计时
        pct     = 1.0 - rem / rsec   # 恢复进度
        dot_c   = 'FF5555'
        val_str = f'${{color FF5555}}{fmt_cd(rem)}${{color}}'
        b       = bar(pct)

    elif api.get('ok') is False:
        # API 确认耗尽 / 无余额
        lbl     = api.get('label', 'N/A')
        dot_c   = 'FF5555'
        val_str = f'${{color FF5555}}{lbl}${{color}}'
        b       = bar(0.0)

    elif api.get('ok') and api.get('pct') is not None:
        # 有真实配额百分比（Kimi 充值后的 Claude 等）
        pct     = api['pct']
        dot_c   = '50FA7B' if pct > 0.5 else ('FFB86C' if pct > 0.2 else 'FF5555')
        val_str = f'${{color 50FA7B}}{api["label"]}${{color}}'
        b       = bar(pct)

    elif api.get('ok'):
        # Key 有效但无配额数字 — 倒计时
        daily   = next_midnight(now)
        dot_c   = '50FA7B'
        val_str = f'${{color FF6644}}{fmt_cd(daily)}${{color}}'
        b       = bar(None)   # 无数据

    else:
        # 无 key
        daily   = next_midnight(now)
        dot_c   = '6A7A99'
        val_str = f'${{color 6A7A99}}{fmt_cd(daily)}${{color}}'
        b       = bar(None)

    dot  = f'${{color {dot_c}}}●${{color}}'
    name_col = f'${{color 6A7A99}}{name:<7}${{color}}'
    lines.append(f'{dot} {name_col} {b} {val_str}')

print('\n'.join(lines))
