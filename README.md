# AI Token Monitor

A lightweight desktop widget that shows real-time token usage and reset countdowns for multiple AI services — rendered inside [Conky](https://github.com/brndnmtthws/conky) on Linux.

```
● Claude  ░░░░░░░░░  无余额
● Gemini  ░░░░░░░░░  配额用完
● Grok    ░░░░░░░░░  耗尽
● Kimi    █████████  22.4M剩
● Codex   ─────────  18:42:01
● Kilo    ─────────  18:42:01
```

## Features

- **HP-bar style progress bars** — colored `█` blocks show quota remaining (green → orange → red)
- **Real API data** — queries Kimi, Grok, Gemini, and Anthropic APIs for live status
- **Reset countdown** — shows time until midnight UTC+8 for services without quota APIs
- **Rate-limit logging** — manually record when you hit a limit; shows recovery countdown
- **Secure key storage** — API keys stored in `~/.config/.ai_monitor_keys` (chmod 600), never logged

## Supported Services

| Service | API Detection | Quota %  | Notes |
|---------|--------------|----------|-------|
| Kimi (Moonshot) | ✅ | ✅ | `/v1/users/me` |
| Grok (xAI) | ✅ | ❌ | 403 = credits exhausted |
| Gemini | ✅ | ❌ | 429 = quota exceeded |
| Claude (Anthropic) | ✅ | via headers | rate-limit headers |
| Codex | ❌ | ❌ | countdown only |
| Kilo | ❌ | ❌ | countdown only |

## Requirements

- Linux with [Conky](https://github.com/brndnmtthws/conky) running
- Python 3.8+
- `pip install requests`

## Quick Install

```bash
git clone https://github.com/luckybbjason1/ai-token-monitor
cd ai-token-monitor
bash install.sh
```

Then edit `~/.config/.ai_monitor_keys` and add your API keys:

```json
{
  "kimi":   "sk-...",
  "grok":   "xai-...",
  "gemini": "AIza...",
  "claude": "sk-ant-..."
}
```

Finally restart Conky:
```bash
pkill conky && conky --daemonize --pause=1
```

## Manual Conky Integration

Add to your `conky.text` block:

```
${execpi 30 python3 ~/token-monitor/conky_ai.py}
```

The fetcher runs as a background cron (every 5 min). The Conky block re-reads the cache every 30 seconds.

## Architecture

```
api_fetcher.py  (cron, every 5 min)
      │  writes
      ▼
api_cache.json  (JSON state file)
      │  reads
      ▼
conky_ai.py     (execpi 30, outputs ${color} tagged text)
      │
      ▼
Conky desktop widget
```

## Manually Recording Rate Limits

If a service doesn't have an API detection, log it in `state.json`:

```json
{
  "Claude": { "limited_at": 1749123456, "reset_h": 5 }
}
```

`limited_at` is a Unix timestamp. The widget shows a recovery countdown.

## Color Scheme

| Color | Meaning |
|-------|---------|
| `#50FA7B` green | Good — quota available |
| `#FFB86C` orange | Warning — below 20% |
| `#FF5555` red | Depleted or rate limited |
| `#6A7A99` gray | No API key configured |
| `#2A3550` dark | Empty bar / no data |

Colors are Dracula-inspired and work well on dark Conky themes.

## Related

- [dibi8.com](https://dibi8.com) — AI tools directory where this was first published
- [Conky docs](https://conky.sourceforge.net/config_settings.html)
- [Moonshot API](https://platform.moonshot.cn/docs)

## License

MIT
