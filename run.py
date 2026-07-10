#!/usr/bin/env python3
"""RapFi 五子棋 - 跨平台启动入口"""
import os, sys, webbrowser, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
from server import main

if __name__ == "__main__":
    port = 18080
    if len(sys.argv) > 1:
        try: port = int(sys.argv[1])
        except: pass
    def _open():
        time.sleep(1.2)
        try: webbrowser.open(f"http://127.0.0.1:{port}/")
        except: pass
    threading.Thread(target=_open, daemon=True).start()
    main()
