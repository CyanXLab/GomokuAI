"""游戏状态管理 - 支持 pve/pvp 模式"""
import threading
from engine_manager import RULE_FREESTYLE, RULE_STANDARD, RULE_RENJU, RULE_NAMES


class GameState:
    def __init__(self):
        self._lock = threading.RLock()
        self.rule = RULE_FREESTYLE
        self.board_size = 15
        self.moves = []
        self.view_index = 0
        self.player_color = 1
        self.game_mode = "pve"
        self.game_over = False
        self.winner = 0
        self.last_error = ""
        self.thinking = False
        # 评估值历史: [{move_num, black_eval, white_eval}]
        self.eval_history = []

    def reset(self, rule=None, board_size=None, player_color=None, game_mode=None):
        with self._lock:
            if rule is not None: self.rule = rule
            if board_size is not None: self.board_size = board_size
            if player_color is not None: self.player_color = player_color
            if game_mode is not None: self.game_mode = game_mode
            self.moves = []
            self.view_index = 0
            self.game_over = False
            self.winner = 0
            self.last_error = ""
            self.thinking = False
            self.eval_history = []

    def get_board(self):
        size = self.board_size
        board = [[0] * size for _ in range(size)]
        for m in self.moves[: self.view_index]:
            if 0 <= m["x"] < size and 0 <= m["y"] < size:
                board[m["x"]][m["y"]] = m["color"]
        return board

    def get_current_color(self):
        """根据 view_index 返回当前该谁下。黑=1, 白=2"""
        if self.view_index == 0: return 1
        last = self.moves[self.view_index - 1]
        return 2 if last["color"] == 1 else 1

    def get_visible_moves(self):
        return self.moves[: self.view_index]

    def add_eval(self, move_num, black_eval, white_eval):
        """添加评估值到历史"""
        with self._lock:
            # 如果回退后重新下，截断后续评估
            if move_num <= len(self.eval_history):
                self.eval_history = self.eval_history[:move_num - 1]
            self.eval_history.append({
                "move": move_num,
                "black": black_eval,
                "white": white_eval,
            })

    def to_dict(self):
        with self._lock:
            return {
                "rule": self.rule,
                "rule_name": RULE_NAMES.get(self.rule, "unknown"),
                "board_size": self.board_size,
                "board": self.get_board(),
                "moves": self.get_visible_moves(),
                "total_moves": len(self.moves),
                "view_index": self.view_index,
                "current_color": self.get_current_color(),
                "player_color": self.player_color,
                "ai_color": 2 if self.player_color == 1 else 1,
                "game_mode": self.game_mode,
                "game_over": self.game_over,
                "winner": self.winner,
                "last_error": self.last_error,
                "thinking": self.thinking,
                "eval_history": self.eval_history[: self.view_index],
            }


_state = GameState()

def get_state():
    return _state
