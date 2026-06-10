#!/bin/bash
# 等桌面环境就绪
sleep 5
export DISPLAY=:0
export XAUTHORITY=/home/bot/.Xauthority
exec python3 /home/bot/ai-token-monitor/monitor.py
