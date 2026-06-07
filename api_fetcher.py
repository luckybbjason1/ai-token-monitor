#!/usr/bin/env python3
"""Background API fetcher — run via cron every 5 min"""

import json, requests, os, locale
from pathlib import Path

KEY_FILE = Path.home() / '.config' / '.ai_monitor_keys'
CACHE    = Path.home() / 'token-monitor' / 'api_cache.json'

# ── Language detection ────────────────────────────────────────
def is_zh():
    for var in ('LANG', 'LANGUAGE', 'LC_ALL', 'LC_MESSAGES'):
        v = os.environ.get(var, '')
        if v.lower().startswith('zh'):
            return True
    try:
        loc = locale.getdefaultlocale()[0] or ''
        return loc.lower().startswith('zh')
    except Exception:
        return False

ZH = is_zh()

def t(zh_text, en_text):
    return zh_text if ZH else en_text

def fmt_remain(remain):
    suffix = t('剩', ' left')
    if remain >= 1_000_000:
        return f'{remain/1_000_000:.1f}M{suffix}'
    elif remain >= 1000:
        return f'{remain//1000}K{suffix}'
    else:
        return f'{remain}{suffix}'

def load_keys():
    try:    return json.loads(KEY_FILE.read_text())
    except Exception: return {}

def save_cache(data):
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(data, indent=2))

keys  = load_keys()
cache = {}

# ── Kimi ─────────────────────────────────────────────────────
key = keys.get('kimi')
if key:
    try:
        r = requests.get('https://api.moonshot.cn/v1/users/me',
                         headers={'Authorization': f'Bearer {key}'}, timeout=8)
        if r.status_code == 200:
            data   = r.json()['data']
            org    = data['organization']
            quota  = org.get('max_token_quota', 0)
            used   = data.get('organization_usage', {}).get('total_tokens', 0)
            remain = max(0, quota - used)
            pct    = remain / quota if quota else 1.0
            cache['Kimi'] = {'ok': True, 'label': fmt_remain(remain), 'pct': pct}
    except Exception:
        pass

# ── Grok ─────────────────────────────────────────────────────
key = keys.get('grok')
if key:
    try:
        r = requests.get('https://api.x.ai/v1/models',
                         headers={'Authorization': f'Bearer {key}'}, timeout=8)
        ok = r.status_code == 200
        cache['Grok'] = {'ok': ok, 'label': 'OK' if ok else t('耗尽', 'Depleted')}
    except Exception:
        cache['Grok'] = {'ok': False, 'label': t('耗尽', 'Depleted')}

# ── Gemini ───────────────────────────────────────────────────
key = keys.get('gemini')
if key:
    try:
        r = requests.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}',
            json={'contents': [{'parts': [{'text': 'hi'}]}],
                  'generationConfig': {'maxOutputTokens': 1}},
            timeout=10)
        if r.status_code == 200:
            cache['Gemini'] = {'ok': True, 'label': 'Key✓'}
        elif r.status_code == 429:
            cache['Gemini'] = {'ok': False, 'label': t('配额用完', 'Quota full')}
        else:
            cache['Gemini'] = {'ok': False, 'label': t('Key无效', 'Key invalid')}
    except Exception:
        pass

# ── Claude ───────────────────────────────────────────────────
key = keys.get('claude')
if key:
    try:
        r = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={'x-api-key': key,
                     'anthropic-version': '2023-06-01',
                     'content-type': 'application/json'},
            json={'model': 'claude-haiku-4-5-20251001',
                  'max_tokens': 1,
                  'messages': [{'role': 'user', 'content': 'hi'}]},
            timeout=10)
        if r.status_code == 200:
            rem_tok = r.headers.get('anthropic-ratelimit-tokens-remaining', '')
            lim_tok = r.headers.get('anthropic-ratelimit-tokens-limit', '')
            if rem_tok and lim_tok:
                rem, lim = int(rem_tok), int(lim_tok)
                cache['Claude'] = {'ok': True, 'label': fmt_remain(rem),
                                   'pct': rem/lim if lim else 1.0}
            else:
                cache['Claude'] = {'ok': True, 'label': 'Key✓'}
        elif r.status_code == 400 and 'credit' in r.text.lower():
            cache['Claude'] = {'ok': False, 'label': t('无余额', 'No balance')}
        elif r.status_code == 429:
            cache['Claude'] = {'ok': False, 'label': t('配额用完', 'Quota full')}
        else:
            cache['Claude'] = {'ok': False, 'label': t('Key无效', 'Key invalid')}
    except Exception:
        pass

save_cache(cache)
print('Cache updated:', list(cache.keys()))
