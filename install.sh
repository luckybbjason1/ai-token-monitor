#!/bin/bash
# AI Token Monitor — one-command installer for Ubuntu + Conky

set -e

INSTALL_DIR="$HOME/token-monitor"
CONFIG_DIR="$HOME/.config"
KEY_FILE="$CONFIG_DIR/.ai_monitor_keys"
AUTOSTART="$HOME/.config/autostart/token-monitor.desktop"

echo "=== AI Token Monitor Installer ==="

# 1. Install dependencies
echo "[1/5] Installing dependencies..."
pip3 install -q requests --break-system-packages 2>/dev/null || pip3 install -q requests
which conky > /dev/null || sudo apt-get install -y conky-all

# 2. Copy files
echo "[2/5] Copying files..."
mkdir -p "$INSTALL_DIR"
cp conky_ai.py api_fetcher.py monitor.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/"*.py

# 3. API keys config
echo "[3/5] Setting up API keys..."
if [ ! -f "$KEY_FILE" ]; then
    cat > "$KEY_FILE" << 'EOF'
{
  "kimi":   "",
  "grok":   "",
  "gemini": "",
  "claude": "",
  "claude_org": ""
}
EOF
    chmod 600 "$KEY_FILE"
    echo "    → Edit $KEY_FILE and fill in your API keys"
else
    echo "    → Key file already exists, skipping"
fi

# 4. Conky integration
echo "[4/5] Conky config..."
CONKY_CONF="$HOME/.config/conky/conky.conf"
if [ -f "$CONKY_CONF" ]; then
    if grep -q "conky_ai.py" "$CONKY_CONF"; then
        echo "    → Already integrated"
    else
        # Insert before the LAST line containing ]]
        last=$(grep -n '\]\]' "$CONKY_CONF" 2>/dev/null | tail -1 | cut -d: -f1)
        if [ -n "$last" ]; then
            sed -i "${last}i\\\${execpi 30 python3 $INSTALL_DIR/conky_ai.py}" "$CONKY_CONF"
            echo "    → Added to existing conky.conf"
        else
            echo "    → Could not find ]] in conky.conf — add this line manually before the closing ]]:"
            echo "      \${execpi 30 python3 $INSTALL_DIR/conky_ai.py}"
        fi
    fi
else
    echo "    → No conky.conf found. Add this line manually to your conky.text:"
    echo '      ${execpi 30 python3 '"$INSTALL_DIR"'/conky_ai.py}'
fi

# 5. Cron for API refresh
echo "[5/5] Setting up cron (every 5 min)..."
(crontab -l 2>/dev/null | grep -v "api_fetcher"; \
 echo "*/5 * * * * python3 $INSTALL_DIR/api_fetcher.py > /dev/null 2>&1") | crontab -

echo ""
echo "=== Done! ==="
echo "1. Fill API keys: nano $KEY_FILE"
echo "2. Restart Conky: pkill conky && conky --daemonize --pause=1"
