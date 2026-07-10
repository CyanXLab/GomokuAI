"""
RapFi 引擎管理器
- 跨平台二进制选择
- 配置文件锁定架构 + 失败回退
- 三种规则自动加载对应模型
- 最强配置：多线程、大置换表、数据库、最大强度
"""
import os
import sys
import json
import platform
import subprocess
import threading
import time
import re


RULE_FREESTYLE = 0
RULE_STANDARD = 1
RULE_RENJU = 2

RULE_NAMES = {0: "freestyle", 1: "standard", 2: "renju"}

RULE_INFO = {
    0: {"name": "自由规则", "desc": "无禁手，五连或长连均胜。黑棋天元开局必胜。"},
    1: {"name": "标准规则", "desc": "无禁手，但有三三、四四等基础限制。"},
    2: {"name": "连珠规则", "desc": "黑棋有三三、四四、长连禁手。黑/白模型分开。"},
}


ENGINE_CANDIDATES = [
    ("x86_64_avxvnni", "engine/pbrain-rapfi-windows-avxvnni.exe", ["windows"]),
    ("x86_64_avxvnni", "engine/pbrain-rapfi-linux-clang-avxvnni", ["linux"]),
    ("x86_64_avx2",    "engine/pbrain-rapfi-windows-avx2.exe",    ["windows"]),
    ("x86_64_avx2",    "engine/pbrain-rapfi-linux-clang-avx2",    ["linux"]),
    ("x86_64_sse",     "engine/pbrain-rapfi-windows-sse.exe",     ["windows"]),
    ("x86_64_sse",     "engine/pbrain-rapfi-linux-clang-sse",     ["linux"]),
    ("arm64",          "engine/pbrain-rapfi-linux-arm64-neon",    ["linux"]),
    ("android_arm64",  "engine/pbrain-rapfi-android-arm64-neon",  ["android"]),
    ("arm64",          "engine/pbrain-rapfi-macos-apple-silicon", ["darwin"]),
]

ARCH_LABELS = {
    "android_arm64": "Android ARM64 (NEON)",
    "arm64": "ARM64 (NEON)",
    "x86_64_avxvnni": "x86_64 (AVX-VNNI)",
    "x86_64_avx2": "x86_64 (AVX2)",
    "x86_64_sse": "x86_64 (SSE)",
}


def _project_dir():
    return os.path.dirname(os.path.abspath(__file__))

def _engine_dir():
    return os.path.join(_project_dir(), "engine")

def _config_path():
    return os.path.join(_project_dir(), "config.json")

def _is_arm64():
    return platform.machine().lower() in ("aarch64", "arm64")

def _current_os():
    system = platform.system().lower()
    if system == "linux":
        if os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA"):
            return "android"
        if os.path.isfile("/system/bin/linker64"):
            return "android"
        if "com.termux" in os.environ.get("PREFIX", "") or "com.termux" in os.environ.get("PATH", ""):
            return "android"
    return system

def _cpu_features():
    feats = set()
    if _is_arm64():
        return feats
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="ignore") as f:
            text = f.read().lower()
            if "avx2" in text: feats.add("avx2")
            if "avxvnni" in text or "avx_vnni" in text: feats.add("avxvnni")
            if "avx512" in text: feats.add("avx512")
            if "sse4_1" in text or "sse41" in text: feats.add("sse")
    except Exception:
        pass
    if sys.platform.startswith("win"):
        feats.add("avx2")
    return feats


def load_config():
    default = {
        "engine": {"architecture": "auto", "max_memory_mb": 512, "thread_num": 0,
                   "timeout_turn_ms": 8000, "timeout_match_ms": 0},
        "game": {"mode": "pve"},
        "rules": {}
    }
    path = _config_path()
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in default["engine"].items():
            cfg.setdefault("engine", {}).setdefault(k, v)
        cfg.setdefault("game", {}).setdefault("mode", "pve")
        cfg.setdefault("rules", {})
        return cfg
    except Exception:
        return default

def save_config(cfg):
    with open(_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


def _matches_arch(arch_tag, target):
    if target == "auto": return True
    if target == "arm64": return arch_tag in ("arm64", "android_arm64")
    if target == "x86_64": return arch_tag.startswith("x86_64")
    return arch_tag == target

def _native_priority(arch_tag):
    current_os = _current_os()
    if current_os == "android":
        return 0 if arch_tag == "android_arm64" else 100
    if _is_arm64():
        return 0 if arch_tag == "arm64" else 100
    feats = _cpu_features()
    if arch_tag in ("arm64", "android_arm64"): return 100
    if arch_tag == "x86_64_avxvnni": return 1 if "avxvnni" in feats else 50
    if arch_tag == "x86_64_avx2": return 4 if "avx2" in feats else 80
    if arch_tag == "x86_64_sse": return 5 if "sse" in feats else 90
    return 99

def get_candidates(target_arch="auto", os_filter=None):
    if os_filter is None:
        os_filter = _current_os()
    here = _project_dir()
    matches = []
    for arch_tag, rel_path, os_list in ENGINE_CANDIDATES:
        if os_filter not in os_list: continue
        if not _matches_arch(arch_tag, target_arch): continue
        abs_path = os.path.join(here, rel_path)
        if not os.path.isfile(abs_path): continue
        matches.append((arch_tag, rel_path, abs_path))
    if target_arch == "auto":
        matches.sort(key=lambda x: _native_priority(x[0]))
    return matches

def list_available_engines(current_os_only=True):
    here = _project_dir()
    current_os = _current_os()
    result = []
    for arch_tag, rel_path, os_list in ENGINE_CANDIDATES:
        abs_path = os.path.join(here, rel_path)
        exists = os.path.isfile(abs_path)
        applicable = current_os in os_list
        if current_os_only and not applicable: continue
        result.append({"arch": arch_tag, "arch_label": ARCH_LABELS.get(arch_tag, arch_tag),
                       "path": rel_path, "available": exists, "applicable": applicable})
    seen = set()
    unique = []
    for e in result:
        if e["arch"] not in seen:
            seen.add(e["arch"])
            unique.append(e)
    return unique


def _try_start_engine(abs_path, engine_dir, timeout=8):
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.Popen([abs_path], cwd=engine_dir, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1, creationflags=creationflags)
    except Exception as e:
        return False, None, f"启动失败: {e}"
    try:
        proc.stdin.write("ABOUT\nEND\n")
        proc.stdin.flush()
        start = time.time()
        name_info = ""
        while time.time() - start < timeout:
            if proc.poll() is not None:
                return False, None, f"进程退出 (code={proc.returncode})"
            line = proc.stdout.readline() if proc.stdout else ""
            if line:
                if "name=" in line:
                    name_info = line.strip()
                    break
            else:
                time.sleep(0.05)
        if not name_info:
            time.sleep(0.5)
            while time.time() - start < timeout + 4:
                line = proc.stdout.readline() if proc.stdout else ""
                if line and "name=" in line:
                    name_info = line.strip()
                    break
                else:
                    if proc.poll() is not None:
                        return False, None, "进程意外退出"
                    time.sleep(0.1)
        try:
            proc.stdin.close()
            proc.terminate()
            try: proc.wait(timeout=2)
            except: proc.kill()
        except: pass
        if not name_info:
            return False, None, "未收到 ABOUT 响应"
        return True, None, name_info
    except Exception as e:
        try: proc.kill()
        except: pass
        return False, None, f"探活异常: {e}"


class RapFiEngine:
    def __init__(self):
        self._proc = None
        self._lock = threading.Lock()
        self._rule = RULE_FREESTYLE
        self._board_size = 15
        self._config = load_config()
        ec = self._config.get("engine", {})
        self._timeout_turn = int(ec.get("timeout_turn_ms", 8000))
        self._timeout_match = int(ec.get("timeout_match_ms", 0))
        self._max_memory = int(ec.get("max_memory_mb", 512))
        self._thread_num = int(ec.get("thread_num", 0))
        self._arch_setting = ec.get("architecture", "auto")
        self._engine_rel_path = None
        self._engine_abs_path = None
        self._engine_arch = None
        self._started = False
        self._start_error = ""
        self._tried_engines = []

    def start(self):
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return True
            self._tried_engines = []
            self._start_error = ""
            engine_dir = _engine_dir()
            candidates = get_candidates(target_arch=self._arch_setting)
            if not candidates:
                if self._arch_setting != "auto":
                    candidates = get_candidates(target_arch="auto")
                if not candidates:
                    self._start_error = "未找到任何可用引擎"
                    return False
            elif self._arch_setting != "auto":
                auto_cands = get_candidates(target_arch="auto")
                tried = set(c[2] for c in candidates)
                candidates = list(candidates) + [c for c in auto_cands if c[2] not in tried]

            for arch_tag, rel_path, abs_path in candidates:
                self._tried_engines.append({"arch": arch_tag, "path": rel_path, "result": "trying"})
                ok, _, info = _try_start_engine(abs_path, engine_dir)
                if not ok:
                    self._tried_engines[-1]["result"] = f"failed: {info[:120]}"
                    self._start_error = f"[{arch_tag}] {info[:200]}"
                    continue
                try:
                    self._start_engine_process(abs_path, engine_dir)
                    self._engine_rel_path = rel_path
                    self._engine_abs_path = abs_path
                    self._engine_arch = arch_tag
                    self._tried_engines[-1]["result"] = "ok"
                    self._started = True
                    self._start_error = ""
                    return True
                except Exception as e:
                    self._tried_engines[-1]["result"] = f"failed: {str(e)[:120]}"
                    self._start_error = f"[{arch_tag}] 启动失败: {e}"
                    try:
                        if self._proc: self._proc.kill(); self._proc = None
                    except: pass
                    continue
            self._start_error = f"所有引擎启动失败 ({len(self._tried_engines)} 个). {self._start_error}"
            return False

    def _start_engine_process(self, abs_path, engine_dir):
        creationflags = 0
        if sys.platform.startswith("win"):
            creationflags = subprocess.CREATE_NO_WINDOW
        self._proc = subprocess.Popen([abs_path], cwd=engine_dir, stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                      text=True, bufsize=1, creationflags=creationflags)
        self._send_raw(f"INFO timeout_turn {self._timeout_turn}")
        self._send_raw(f"INFO timeout_match {self._timeout_match}")
        self._send_raw(f"INFO max_memory {self._max_memory}")
        self._send_raw(f"INFO thread_num {self._thread_num}")
        self._send_raw(f"INFO rule {self._rule}")
        self._send_raw("INFO usedatabase 1")
        self._send_raw("INFO strength 100")
        self._send_raw("INFO search_type alphabeta")
        self._send_raw(f"START {self._board_size}")
        self._read_until_ok_or_error()

    def stop(self):
        with self._lock:
            if self._proc is None: return
            try:
                if self._proc.poll() is None:
                    try:
                        self._proc.stdin.write("END\n"); self._proc.stdin.flush()
                    except: pass
                    try: self._proc.wait(timeout=2)
                    except: self._proc.kill()
            finally:
                self._proc = None
                self._started = False

    def restart(self):
        self.stop(); time.sleep(0.1); return self.start()

    @property
    def started(self):
        return self._started and self._proc is not None and self._proc.poll() is None

    def set_rule(self, rule):
        rule = int(rule)
        if rule not in (0, 1, 2): raise ValueError(f"无效规则: {rule}")
        if rule == self._rule and self.started: return
        self._rule = rule
        self.restart()

    def set_board_size(self, size):
        size = int(size)
        if size < 5 or size > 30: raise ValueError(f"无效棋盘: {size}")
        if size == self._board_size: return
        self._board_size = size
        self.restart()

    def set_timeout_turn(self, ms):
        self._timeout_turn = int(ms)
        self._config["engine"]["timeout_turn_ms"] = self._timeout_turn
        save_config(self._config)
        if self.started: self._send_raw(f"INFO timeout_turn {self._timeout_turn}")

    def set_max_memory(self, mb):
        self._max_memory = int(mb)
        self._config["engine"]["max_memory_mb"] = self._max_memory
        save_config(self._config)
        if self.started: self._send_raw(f"INFO max_memory {self._max_memory}")

    def set_thread_num(self, n):
        self._thread_num = int(n)
        self._config["engine"]["thread_num"] = self._thread_num
        save_config(self._config)
        if self.started: self._send_raw(f"INFO thread_num {self._thread_num}")

    def set_architecture(self, arch):
        self._arch_setting = arch
        self._config["engine"]["architecture"] = arch
        save_config(self._config)
        return self.restart()

    def get_config(self):
        return {
            "rule": self._rule, "rule_name": RULE_NAMES.get(self._rule, "unknown"),
            "board_size": self._board_size, "timeout_turn": self._timeout_turn,
            "timeout_match": self._timeout_match, "max_memory": self._max_memory,
            "thread_num": self._thread_num, "engine_path": self._engine_rel_path,
            "engine_arch": self._engine_arch,
            "engine_arch_label": ARCH_LABELS.get(self._engine_arch, self._engine_arch or "unknown"),
            "arch_setting": self._arch_setting, "started": self.started,
            "start_error": self._start_error, "tried_engines": self._tried_engines,
            "platform": _current_os(), "arch": platform.machine().lower(),
            "available_engines": list_available_engines(current_os_only=True),
        }

    def _send_raw(self, line):
        if self._proc is None or self._proc.poll() is not None:
            raise RuntimeError("引擎未运行")
        self._proc.stdin.write(line + "\n"); self._proc.stdin.flush()

    def _read_line(self):
        if self._proc is None: return ""
        line = self._proc.stdout.readline()
        return line.rstrip("\r\n") if line else ""

    def _read_until_ok_or_error(self, max_lines=200):
        for _ in range(max_lines):
            line = self._read_line()
            if not line: break
            if line.strip() == "OK": break
            if line.startswith("ERROR"): break

    def _parse_move_response(self):
        messages = []; move = None
        for _ in range(500):
            line = self._read_line()
            if not line: break
            messages.append(line)
            stripped = line.strip()
            if stripped.startswith("MESSAGE"): continue
            if stripped.startswith("ERROR"): raise RuntimeError("引擎错误: " + stripped)
            if stripped == "OK": continue
            m = re.match(r"^(-?\d+),(-?\d+)$", stripped)
            if m:
                move = (int(m.group(1)), int(m.group(2))); break
        return move, messages

    def think(self, moves, engine_color):
        with self._lock:
            if not self.started:
                if not self.start(): raise RuntimeError(f"引擎启动失败: {self._start_error}")
            self._send_raw("BOARD")
            for x, y, c in moves:
                self._send_raw(f"{x},{y},{c}")
            self._send_raw("DONE")
            move, messages = self._parse_move_response()
            if move is None:
                raise RuntimeError(f"引擎未返回落子: {messages[-3:] if messages else 'empty'}")
            return move


_engine = None
_engine_lock = threading.Lock()

def get_engine():
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = RapFiEngine()
        return _engine
