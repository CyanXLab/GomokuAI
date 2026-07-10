"""游戏状态管理 - 支持 pve/pvp 模式"""
import threading
from engine_manager import RULE_FREESTYLE, RULE_STANDARD, RULE_RENJU, RULE_NAMES


class GameState:
    def __init__(self):
        self._lock = threading.RLock()  # 可重入锁，避免 to_dict 在 lock 内调用死锁
        self.rule = RULE_FREESTYLE
        self.board_size = 15
        self.moves = []
        self.view_index = 0
        self.player_color = 1
        self.game_mode = "pve"
        self.auto_play = False
        self.auto_play_delay = 500
        self.game_over = False
        self.winner = 0
        self.last_error = ""
        self.thinking = False

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
            self.auto_play = False

    def get_board(self):
        size = self.board_size
        board = [[0] * size for _ in range(size)]
        for m in self.moves[: self.view_index]:
            if 0 <= m["x"] < size and 0 <= m["y"] < size:
                board[m["x"]][m["y"]] = m["color"]
        return board

    def get_current_color(self):
        if self.view_index == 0: return 1
        last = self.moves[self.view_index - 1]
        return 2 if last["color"] == 1 else 1

    def get_visible_moves(self):
        return self.moves[: self.view_index]

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
                "auto_play": self.auto_play,
                "auto_play_delay": self.auto_play_delay,
                "game_over": self.game_over,
                "winner": self.winner,
                "last_error": self.last_error,
                "thinking": self.thinking,
            }


_state = GameState()

def get_state():
    return _state
