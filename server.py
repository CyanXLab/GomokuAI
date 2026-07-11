"""
RapFi 在线五子棋 Flask 后端
- pve/pvp 模式
- 游戏结束后可从历史位置继续
- 无回合限制
- 评估值历史
"""
import os
import sys
import json
import threading
import time
import traceback

from flask import Flask, request, jsonify, send_from_directory

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from engine_manager import (
    get_engine, RULE_FREESTYLE, RULE_STANDARD, RULE_RENJU,
    RULE_NAMES, RULE_INFO,
)
from game_state import get_state

app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.after_request
def add_no_cache_headers(resp):
    if request.path.startswith("/static/") or request.path == "/" or request.path.endswith(".html"):
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    return resp


def _ok(data=None):
    return {"ok": True, "data": data or {}}

def _err(msg, data=None):
    return {"ok": False, "error": msg, "data": data or {}}


def _check_win_from_board(board, x, y, color, rule):
    size = len(board)
    for dx, dy in [(1,0),(0,1),(1,1),(1,-1)]:
        count = 1
        nx, ny = x+dx, y+dy
        while 0 <= nx < size and 0 <= ny < size and board[nx][ny] == color:
            count += 1; nx += dx; ny += dy
        nx, ny = x-dx, y-dy
        while 0 <= nx < size and 0 <= ny < size and board[nx][ny] == color:
            count += 1; nx -= dx; ny -= dy
        if count >= 5:
            return True
    return False


def _check_win(state):
    if not state.moves: return False
    last = state.moves[-1]
    return _check_win_from_board(state.get_board(), last["x"], last["y"], last["color"], state.rule)


def _get_eval_from_engine(state, moves_list):
    """从引擎获取当前局面的评估值。返回 (black_eval, white_eval)。
    使用 YXBEVALUATE 命令或简单的局面评估。"""
    try:
        engine = get_engine()
        # RapFi 没有直接的评估命令，我们用 BOARD + 短时间搜索来获取评估
        # 这里用一个简单方法：发送局面，看引擎返回的 Eval 值
        # 但这会触发完整搜索，太慢。
        # 替代方案：用局面统计（棋型数量）作为简单评估
        board = state.get_board()
        size = state.board_size
        black_score = 0
        white_score = 0
        # 简单评估：计算每方的棋型分数
        # 五连=100000, 活四=10000, 冲四=1000, 活三=100, 眠三=10, 活二=1
        for x in range(size):
            for y in range(size):
                if board[x][y] == 0: continue
                color = board[x][y]
                score = _count_patterns(board, x, y, color, size)
                if color == 1:
                    black_score += score
                else:
                    white_score += score
        # 归一化到 -1000 ~ 1000
        diff = black_score - white_score
        eval_val = max(-1000, min(1000, diff))
        return eval_val, -eval_val
    except Exception as e:
        print(f"[EVAL] 错误: {e}", flush=True)
        return 0, 0


def _count_patterns(board, x, y, color, size):
    """统计某位置的棋型分数"""
    total = 0
    for dx, dy in [(1,0),(0,1),(1,1),(1,-1)]:
        count = 1
        blocked = 0
        nx, ny = x+dx, y+dy
        while 0 <= nx < size and 0 <= ny < size and board[nx][ny] == color:
            count += 1; nx += dx; ny += dy
        if not (0 <= nx < size and 0 <= ny < size) or board[nx][ny] != 0:
            blocked += 1
        nx, ny = x-dx, y-dy
        while 0 <= nx < size and 0 <= ny < size and board[nx][ny] == color:
            count += 1; nx -= dx; ny -= dy
        if not (0 <= nx < size and 0 <= ny < size) or board[nx][ny] != 0:
            blocked += 1
        # 计分
        if count >= 5: total += 100000
        elif count == 4 and blocked == 0: total += 10000
        elif count == 4: total += 1000
        elif count == 3 and blocked == 0: total += 100
        elif count == 3: total += 10
        elif count == 2 and blocked == 0: total += 5
        elif count == 2: total += 1
    return total


def do_new_game(rule, board_size, player_color, game_mode, timeout_turn, thread_num, max_memory):
    state = get_state()
    engine = get_engine()

    print(f"[NEW_GAME] rule={rule}, size={board_size}, color={player_color}, mode={game_mode}", flush=True)

    if timeout_turn is not None: engine.set_timeout_turn(timeout_turn)
    if thread_num is not None: engine.set_thread_num(thread_num)
    if max_memory is not None: engine.set_max_memory(max_memory)

    engine.set_rule(rule)
    engine.set_board_size(board_size)

    state.reset(rule=rule, board_size=board_size, player_color=player_color, game_mode=game_mode)
    print(f"[NEW_GAME] 状态已重置, thinking={state.thinking}", flush=True)

    if game_mode == "pve" and player_color == 2:
        print(f"[NEW_GAME] pve 玩家执白, AI 先手", flush=True)
        state.thinking = True
        try:
            move = engine.think([], engine_color=1)
            print(f"[NEW_GAME] AI 首手: ({move[0]},{move[1]})", flush=True)
            state.moves.append({"x": move[0], "y": move[1], "color": 1, "by": "ai"})
            state.view_index = len(state.moves)
            # 记录评估
            b_eval, w_eval = _get_eval_from_engine(state, state.get_visible_moves())
            state.add_eval(1, b_eval, w_eval)
        except Exception as e:
            state.last_error = str(e)
            print(f"[NEW_GAME] AI 错误: {e}", flush=True)
            traceback.print_exc()
        finally:
            state.thinking = False

    return _ok(state.to_dict())


def do_player_move(x, y):
    """玩家下子。pve 模式 AI 自动应招。"""
    state = get_state()
    engine = get_engine()

    print(f"[MOVE] 玩家请求 ({x},{y}), mode={state.game_mode}, thinking={state.thinking}", flush=True)

    with state._lock:
        if state.thinking:
            return _err("引擎思考中，请稍候")

        if state.view_index < len(state.moves) or state.game_over:
            print(f"[MOVE] 截断: {len(state.moves)} -> {state.view_index}", flush=True)
            state.moves = state.moves[: state.view_index]
            state.game_over = False
            state.winner = 0

        current_color = state.get_current_color()
        print(f"[MOVE] 玩家颜色: {current_color}", flush=True)

        board = state.get_board()
        if not (0 <= x < state.board_size and 0 <= y < state.board_size):
            return _err("坐标超出棋盘")
        if board[x][y] != 0:
            return _err("该位置已有棋子")

        state.moves.append({"x": x, "y": y, "color": current_color, "by": "human"})
        state.view_index = len(state.moves)
        print(f"[MOVE] 已下子, 步数={len(state.moves)}", flush=True)

        # 记录评估
        b_eval, w_eval = _get_eval_from_engine(state, state.get_visible_moves())
        state.add_eval(len(state.moves), b_eval, w_eval)

        if _check_win(state):
            state.game_over = True
            state.winner = current_color
            state.thinking = False
            print(f"[MOVE] 游戏结束! 胜者={current_color}", flush=True)
            return _ok(state.to_dict())

    # pve 模式：AI 自动应招
    if state.game_mode == "pve":
        # AI 应招的颜色 = 当前该下的颜色（玩家下完后自动切换）
        ai_color = state.get_current_color()
        print(f"[MOVE] pve AI 应招, ai_color={ai_color}", flush=True)
        state.thinking = True
        try:
            engine.set_rule(state.rule)
            visible = [(m["x"], m["y"], m["color"]) for m in state.get_visible_moves()]
            move = engine.think(visible, engine_color=ai_color)
            print(f"[MOVE] AI 返回: ({move[0]},{move[1]})", flush=True)
            with state._lock:
                state.moves.append({"x": move[0], "y": move[1], "color": ai_color, "by": "ai"})
                state.view_index = len(state.moves)
                # 记录评估
                b_eval, w_eval = _get_eval_from_engine(state, state.get_visible_moves())
                state.add_eval(len(state.moves), b_eval, w_eval)
                if _check_win(state):
                    state.game_over = True
                    state.winner = ai_color
                    print(f"[MOVE] AI 获胜!", flush=True)
        except Exception as e:
            state.last_error = str(e)
            print(f"[MOVE] AI 错误: {e}", flush=True)
            traceback.print_exc()
        finally:
            state.thinking = False
            print(f"[MOVE] AI 思考结束", flush=True)

    return _ok(state.to_dict())


def do_ai_move():
    """AI 单步下子（不触发自动应招）"""
    state = get_state()
    engine = get_engine()

    print(f"[AI_MOVE] 请求, mode={state.game_mode}, thinking={state.thinking}", flush=True)

    with state._lock:
        if state.thinking:
            return _err("引擎思考中")

        if state.view_index < len(state.moves) or state.game_over:
            print(f"[AI_MOVE] 截断: {len(state.moves)} -> {state.view_index}", flush=True)
            state.moves = state.moves[: state.view_index]
            state.game_over = False
            state.winner = 0

        current_color = state.get_current_color()
        print(f"[AI_MOVE] AI 颜色: {current_color}", flush=True)

    state.thinking = True
    try:
        engine.set_rule(state.rule)
        visible = [(m["x"], m["y"], m["color"]) for m in state.get_visible_moves()]
        move = engine.think(visible, engine_color=current_color)
        print(f"[AI_MOVE] AI 返回: ({move[0]},{move[1]})", flush=True)
        with state._lock:
            state.moves.append({"x": move[0], "y": move[1], "color": current_color, "by": "ai"})
            state.view_index = len(state.moves)
            # 记录评估
            b_eval, w_eval = _get_eval_from_engine(state, state.get_visible_moves())
            state.add_eval(len(state.moves), b_eval, w_eval)
            if _check_win(state):
                state.game_over = True
                state.winner = current_color
                print(f"[AI_MOVE] AI 获胜!", flush=True)
    except Exception as e:
        state.last_error = str(e)
        print(f"[AI_MOVE] 错误: {e}", flush=True)
        traceback.print_exc()
    finally:
        state.thinking = False
        print(f"[AI_MOVE] 完成", flush=True)

    return _ok(state.to_dict())


def do_undo():
    state = get_state()
    with state._lock:
        if state.view_index <= 0:
            return _err("已经是棋局开始")
        state.view_index -= 1
    return _ok(state.to_dict())

def do_redo():
    state = get_state()
    with state._lock:
        if state.view_index >= len(state.moves):
            return _err("已经是最新的")
        state.view_index += 1
    return _ok(state.to_dict())

def do_jump(index):
    state = get_state()
    with state._lock:
        if index < 0 or index > len(state.moves):
            return _err("无效的步骤索引")
        state.view_index = index
    return _ok(state.to_dict())


def do_update_config(timeout_turn=None, thread_num=None, max_memory=None, timeout_match=None):
    engine = get_engine()
    if timeout_turn is not None: engine.set_timeout_turn(timeout_turn)
    if thread_num is not None: engine.set_thread_num(thread_num)
    if max_memory is not None: engine.set_max_memory(max_memory)
    if timeout_match is not None: engine.set_timeout_match(timeout_match)
    return _ok({"config": engine.get_config(), "state": get_state().to_dict()})


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/api/state")
def api_state():
    return jsonify(_ok(get_state().to_dict()))

@app.route("/api/config")
def api_config():
    return jsonify(_ok(get_engine().get_config()))

@app.route("/api/rules")
def api_rules():
    return jsonify(_ok([{"id": k, "name": v["name"], "desc": v["desc"]} for k, v in RULE_INFO.items()]))

@app.route("/api/engines")
def api_engines():
    from engine_manager import list_available_engines, get_candidates, _current_os
    return jsonify(_ok({
        "engines": list_available_engines(current_os_only=True),
        "current_os": _current_os(),
        "auto_candidate_order": [c[0] for c in get_candidates(target_arch="auto")],
    }))


@app.route("/api/new_game", methods=["POST"])
def api_new_game():
    body = request.get_json(force=True, silent=True) or {}
    try:
        rule = int(body.get("rule", 0))
        board_size = int(body.get("board_size", 15))
        player_color = int(body.get("player_color", 1))
        game_mode = body.get("game_mode", "pve")
        if game_mode not in ("pve", "pvp"): game_mode = "pve"
        timeout_turn = body.get("timeout_turn")
        thread_num = body.get("thread_num")
        max_memory = body.get("max_memory")
        if timeout_turn is not None: timeout_turn = int(timeout_turn)
        if thread_num is not None: thread_num = int(thread_num)
        if max_memory is not None: max_memory = int(max_memory)
        return jsonify(do_new_game(rule, board_size, player_color, game_mode, timeout_turn, thread_num, max_memory))
    except Exception as e:
        traceback.print_exc()
        return jsonify(_err(str(e))), 500

@app.route("/api/move", methods=["POST"])
def api_move():
    body = request.get_json(force=True, silent=True) or {}
    return jsonify(do_player_move(int(body.get("x", -1)), int(body.get("y", -1))))

@app.route("/api/ai_move", methods=["POST"])
def api_ai_move():
    return jsonify(do_ai_move())

@app.route("/api/undo", methods=["POST"])
def api_undo():
    return jsonify(do_undo())

@app.route("/api/redo", methods=["POST"])
def api_redo():
    return jsonify(do_redo())

@app.route("/api/jump", methods=["POST"])
def api_jump():
    body = request.get_json(force=True, silent=True) or {}
    return jsonify(do_jump(int(body.get("index", 0))))

@app.route("/api/config", methods=["POST"])
def api_config_update():
    body = request.get_json(force=True, silent=True) or {}
    return jsonify(do_update_config(
        timeout_turn=body.get("timeout_turn"),
        thread_num=body.get("thread_num"),
        max_memory=body.get("max_memory"),
        timeout_match=body.get("timeout_match"),
    ))

@app.route("/api/architecture", methods=["POST"])
def api_set_arch():
    body = request.get_json(force=True, silent=True) or {}
    arch = body.get("arch", "auto")
    engine = get_engine()
    try:
        success = engine.set_architecture(arch)
        return jsonify(_ok({"config": engine.get_config(), "state": get_state().to_dict(), "success": success}))
    except Exception as e:
        return jsonify(_err(str(e))), 500

@app.route("/api/test_engine", methods=["POST"])
def api_test_engine():
    body = request.get_json(force=True, silent=True) or {}
    arch = body.get("arch", "auto")
    from engine_manager import get_candidates, _try_start_engine, _engine_dir
    candidates = get_candidates(target_arch=arch)
    if not candidates:
        return jsonify(_err(f"未找到匹配架构 '{arch}' 的引擎")), 404
    results = []
    for arch_tag, rel_path, abs_path in candidates:
        ok, _, info = _try_start_engine(abs_path, _engine_dir())
        results.append({"arch": arch_tag, "path": rel_path, "success": ok, "info": info if ok else info[:200]})
        if ok: break
    return jsonify(_ok({"results": results}))


def main():
    port = 18080
    if len(sys.argv) > 1:
        try: port = int(sys.argv[1])
        except: pass

    print("=" * 60, flush=True)
    print("  GomokuPrime (Flask)", flush=True)
    print("=" * 60, flush=True)
    try:
        from engine_manager import list_available_engines, _current_os
        import platform
        print(f"[INFO] 平台: {_current_os()} {platform.machine()}", flush=True)
        avail = [e for e in list_available_engines(current_os_only=True) if e["available"]]
        print(f"[INFO] 可用引擎: {len(avail)} 个", flush=True)
        for e in avail:
            print(f"       - {e['arch_label']}", flush=True)
        engine = get_engine()
        success = engine.start()
        cfg = engine.get_config()
        if success:
            print(f"\n[OK] 引擎: {cfg['engine_path']}", flush=True)
            print(f"     架构: {cfg['engine_arch_label']}", flush=True)
            print(f"     规则: {RULE_INFO[cfg['rule']]['name']}", flush=True)
        else:
            print(f"\n[WARN] 引擎启动失败: {cfg.get('start_error','')[:200]}", flush=True)
    except Exception as e:
        print(f"[WARN] 引擎异常: {e}", flush=True)
        traceback.print_exc()

    print(f"\n[OK] 服务: http://127.0.0.1:{port}/", flush=True)
    print("    Ctrl+C 退出\n", flush=True)

    import logging
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    try:
        app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n[退出] 关闭引擎...", flush=True)
        get_engine().stop()
        print("[完成]", flush=True)


if __name__ == "__main__":
    main()
