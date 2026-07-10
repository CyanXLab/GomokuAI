/**
 * RapFi 五子棋前端 - 棋子序号 + 双人模式 + AI 单步 + 无回合限制
 */

const API = {
    async get(path) { const r = await fetch(path); return r.json(); },
    async post(path, body) {
        const r = await fetch(path, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body || {}),
        });
        return r.json();
    },
};

const State = {
    rule: 0, ruleName: "freestyle", boardSize: 15,
    board: [], moves: [], totalMoves: 0, viewIndex: 0,
    currentColor: 1, playerColor: 1, aiColor: 2,
    gameMode: "pve", gameOver: false, winner: 0,
    thinking: false, lastError: "",
    pendingMove: null, hoverPos: null,
};

const RULE_INFO = {
    0: { name: "自由规则", desc: "无禁手，五连或长连均胜。黑棋天元开局必胜。" },
    1: { name: "标准规则", desc: "无禁手，但有三三、四四等基础限制。" },
    2: { name: "连珠规则", desc: "黑棋有三三、四四、长连禁手。黑/白模型分开。" },
};

const $ = (id) => document.getElementById(id);
const canvas = $("board");
const ctx = canvas.getContext("2d");

// ============= 棋盘渲染 =============
function resizeCanvas() {
    const wrapper = canvas.parentElement;
    const rect = wrapper.getBoundingClientRect();
    const size = Math.max(280, Math.min(rect.width - 24, rect.height - 24));
    const dpr = window.devicePixelRatio || 1;
    canvas.style.width = size + "px";
    canvas.style.height = size + "px";
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawBoard();
}

function drawBoard() {
    const size = State.boardSize;
    const cssW = parseFloat(canvas.style.width) || canvas.width;
    const padding = cssW * 0.045;
    const cellSize = (cssW - padding * 2) / (size - 1);

    // 棋盘背景
    const grad = ctx.createLinearGradient(0, 0, cssW, cssW);
    grad.addColorStop(0, "#d4a368");
    grad.addColorStop(0.5, "#c8965a");
    grad.addColorStop(1, "#b8854a");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, cssW, cssW);

    // 内阴影
    const innerGrad = ctx.createRadialGradient(cssW/2, cssW/2, cssW*0.3, cssW/2, cssW/2, cssW*0.7);
    innerGrad.addColorStop(0, "rgba(0,0,0,0)");
    innerGrad.addColorStop(1, "rgba(0,0,0,0.2)");
    ctx.fillStyle = innerGrad;
    ctx.fillRect(0, 0, cssW, cssW);

    // 网格线
    ctx.strokeStyle = "rgba(70, 40, 20, 0.85)";
    ctx.lineWidth = 1;
    for (let i = 0; i < size; i++) {
        const p = padding + i * cellSize;
        ctx.beginPath(); ctx.moveTo(padding, p); ctx.lineTo(cssW - padding, p); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(p, padding); ctx.lineTo(p, cssW - padding); ctx.stroke();
    }
    // 边框
    ctx.strokeStyle = "rgba(70, 40, 20, 1)";
    ctx.lineWidth = 2;
    ctx.strokeRect(padding, padding, cssW - padding*2, cssW - padding*2);

    // 星位
    const stars = getStarPoints(size);
    ctx.fillStyle = "rgba(70, 40, 20, 0.9)";
    for (const [sx, sy] of stars) {
        ctx.beginPath();
        ctx.arc(padding + sx*cellSize, padding + sy*cellSize, Math.max(2.5, cellSize*0.07), 0, Math.PI*2);
        ctx.fill();
    }

    // 坐标标签
    ctx.fillStyle = "rgba(70, 40, 20, 0.7)";
    ctx.font = `${Math.max(9, cellSize*0.22)}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    for (let i = 0; i < size; i++) {
        const p = padding + i * cellSize;
        ctx.fillText(String.fromCharCode(65 + i), p, padding * 0.5);
        ctx.fillText(String(size - i), padding * 0.5, p);
    }

    // 绘制棋子 + 序号
    const visibleMoves = State.moves.slice(0, State.viewIndex);
    for (let i = 0; i < visibleMoves.length; i++) {
        const m = visibleMoves[i];
        drawStone(m.x, m.y, m.color, cellSize, padding, false);
        // 在棋子中间绘制序号
        drawMoveNumber(m.x, m.y, m.color, i + 1, cellSize, padding);
    }

    // 标记最后一步
    if (State.viewIndex > 0) {
        const last = State.moves[State.viewIndex - 1];
        const px = padding + last.x * cellSize;
        const py = padding + last.y * cellSize;
        ctx.strokeStyle = "#ff4d6d";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.arc(px, py, cellSize * 0.16, 0, Math.PI * 2);
        ctx.stroke();
    }

    // 待确认落子
    if (State.pendingMove) {
        const { x, y } = State.pendingMove;
        drawStone(x, y, State.currentColor, cellSize, padding, true);
        const px = padding + x * cellSize;
        const py = padding + y * cellSize;
        ctx.strokeStyle = "#fbbf24";
        ctx.lineWidth = 2.5;
        ctx.setLineDash([5, 4]);
        ctx.beginPath();
        ctx.arc(px, py, cellSize * 0.46, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
    } else if (State.hoverPos && !State.gameOver && !State.thinking) {
        const { x, y } = State.hoverPos;
        if (State.board[x] && State.board[x][y] === 0) {
            drawStone(x, y, State.currentColor, cellSize, padding, true);
        }
    }
}

function drawStone(x, y, color, cellSize, padding, preview) {
    const px = padding + x * cellSize;
    const py = padding + y * cellSize;
    const r = cellSize * 0.43;
    ctx.save();
    if (preview) ctx.globalAlpha = 0.5;
    ctx.shadowColor = "rgba(0,0,0,0.55)";
    ctx.shadowBlur = 5;
    ctx.shadowOffsetX = 1;
    ctx.shadowOffsetY = 2;
    const grad = ctx.createRadialGradient(px - r*0.35, py - r*0.35, r*0.1, px, py, r);
    if (color === 1) {
        grad.addColorStop(0, "#6a6a6a"); grad.addColorStop(0.5, "#2a2a2a"); grad.addColorStop(1, "#050505");
    } else {
        grad.addColorStop(0, "#ffffff"); grad.addColorStop(0.5, "#f0f0f0"); grad.addColorStop(1, "#b0b0b0");
    }
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(px, py, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
}

function drawMoveNumber(x, y, color, num, cellSize, padding) {
    const px = padding + x * cellSize;
    const py = padding + y * cellSize;
    const fontSize = Math.max(10, cellSize * 0.32);
    ctx.save();
    ctx.font = `bold ${fontSize}px sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    // 黑棋上显示白字，白棋上显示黑字
    ctx.fillStyle = color === 1 ? "#ffffff" : "#000000";
    ctx.fillText(String(num), px, py);
    ctx.restore();
}

function getStarPoints(size) {
    if (size === 15) return [[3,3],[3,11],[11,3],[11,11],[7,7]];
    if (size === 19) return [[3,3],[3,9],[3,15],[9,3],[9,9],[9,15],[15,3],[15,9],[15,15]];
    if (size === 13) return [[3,3],[3,9],[9,3],[9,9],[6,6]];
    return [];
}

// ============= 鼠标/触摸事件 =============
function pixelToCell(px, py) {
    const cssW = parseFloat(canvas.style.width) || canvas.width;
    const padding = cssW * 0.045;
    const cellSize = (cssW - padding * 2) / (State.boardSize - 1);
    const x = Math.round((px - padding) / cellSize);
    const y = Math.round((py - padding) / cellSize);
    if (x < 0 || x >= State.boardSize || y < 0 || y >= State.boardSize) return null;
    return { x, y };
}

canvas.addEventListener("mousemove", (e) => {
    const rect = canvas.getBoundingClientRect();
    const cell = pixelToCell(e.clientX - rect.left, e.clientY - rect.top);
    if (cell && (!State.hoverPos || State.hoverPos.x !== cell.x || State.hoverPos.y !== cell.y)) {
        State.hoverPos = cell;
        drawBoard();
    } else if (!cell && State.hoverPos) {
        State.hoverPos = null;
        drawBoard();
    }
});

canvas.addEventListener("mouseleave", () => {
    State.hoverPos = null;
    drawBoard();
});

canvas.addEventListener("click", handleBoardClick);

function handleBoardClick(e) {
    if (State.thinking) {
        toast("引擎思考中，请稍候", "error");
        return;
    }

    const rect = canvas.getBoundingClientRect();
    const cell = pixelToCell(e.clientX - rect.left, e.clientY - rect.top);
    if (!cell) return;

    if (State.board[cell.x][cell.y] !== 0) {
        toast("该位置已有棋子", "error");
        State.pendingMove = null;
        drawBoard();
        return;
    }

    // 两次点击确认
    if (State.pendingMove && State.pendingMove.x === cell.x && State.pendingMove.y === cell.y) {
        const move = State.pendingMove;
        State.pendingMove = null;
        confirmMove(move.x, move.y);
    } else {
        State.pendingMove = cell;
        if (State.viewIndex < State.totalMoves) {
            setHint("再次点击确认（将从此步开始新的对局）", "warn");
        } else {
            setHint("再次点击同一位置确认落子", "warn");
        }
        drawBoard();
    }
}

canvas.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    if (State.pendingMove) {
        State.pendingMove = null;
        setHint("点击棋盘交叉点选择落子，再次点击确认");
        drawBoard();
    }
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && State.pendingMove) {
        State.pendingMove = null;
        setHint("点击棋盘交叉点选择落子，再次点击确认");
        drawBoard();
    }
    if (e.key === "ArrowLeft") $("btnBack").click();
    if (e.key === "ArrowRight") $("btnForward").click();
});

async function confirmMove(x, y) {
    // pvp 模式不显示思考状态（只有 pve 模式 AI 应招时才需要）
    const isPvp = State.gameMode === "pvp";
    if (!isPvp) setThinking(true);
    try {
        const res = await API.post("/api/move", { x, y });
        if (res.ok) {
            updateFromServer(res.data);
        } else {
            toast(res.error || "下子失败", "error");
        }
    } catch (err) {
        toast("网络错误: " + err.message, "error");
    } finally {
        if (!isPvp) setThinking(false);
    }
}

// ============= UI 更新 =============
function updateFromServer(data) {
    State.rule = data.rule;
    State.ruleName = data.rule_name;
    State.boardSize = data.board_size;
    State.board = data.board;
    State.moves = data.moves;
    State.totalMoves = data.total_moves;
    State.viewIndex = data.view_index;
    State.currentColor = data.current_color;
    State.playerColor = data.player_color;
    State.aiColor = data.ai_color;
    State.gameMode = data.game_mode;
    State.gameOver = data.game_over;
    State.winner = data.winner;
    State.thinking = data.thinking;
    State.lastError = data.last_error || "";
    renderAll();
}

function renderAll() {
    drawBoard();
    renderStatusBar();
    renderMoveList();
    renderControls();
    renderRuleHint();
    renderTurnStone();
}

function renderStatusBar() {
    $("statusRule").textContent = RULE_INFO[State.rule]?.name || "未知";
    const turnEl = $("statusTurn");
    if (State.gameOver) {
        if (State.winner === 1) turnEl.textContent = "黑棋胜";
        else if (State.winner === 2) turnEl.textContent = "白棋胜";
        else turnEl.textContent = "平局";
    } else {
        turnEl.textContent = State.currentColor === 1 ? "黑棋" : "白棋";
    }
    $("statusStep").textContent = `${State.viewIndex}/${State.totalMoves}`;
    $("statusMode").textContent = State.gameMode === "pve" ? "人机" : "双人";

    const resultEl = $("statusResult");
    if (State.gameOver) {
        resultEl.classList.remove("hidden");
        const isPlayerWin = State.winner === State.playerColor;
        resultEl.textContent = isPlayerWin ? "玩家获胜！" : (State.winner === 0 ? "平局" : "AI 获胜");
    } else {
        resultEl.classList.add("hidden");
    }
}

function renderTurnStone() {
    const stone = $("turnStone");
    if (State.currentColor === 1) {
        stone.style.background = "radial-gradient(circle at 30% 30%, #5a5a5a, #0a0a0a)";
    } else {
        stone.style.background = "radial-gradient(circle at 30% 30%, #ffffff, #b0b0b0)";
    }
}

function renderMoveList() {
    const list = $("moveList");
    if (State.moves.length === 0) {
        list.innerHTML = '<div class="empty-hint">尚未开始对局</div>';
        return;
    }
    const size = State.boardSize;
    let html = "";
    for (let i = 0; i < State.moves.length; i++) {
        const m = State.moves[i];
        const coord = coordLabel(m.x, m.y, size);
        const isCurrent = (i === State.viewIndex - 1);
        html += `<div class="move-item ${isCurrent ? "current" : ""}" data-index="${i + 1}">
            <span class="move-num">${i + 1}.</span>
            <span class="move-stone ${m.color === 1 ? "black" : "white"}"></span>
            <span class="move-coord">${coord}</span>
            <span class="move-by ${m.by}">${m.by === "ai" ? "AI" : "玩家"}</span>
        </div>`;
    }
    list.innerHTML = html;
    list.querySelectorAll(".move-item").forEach((el) => {
        el.addEventListener("click", () => {
            jumpTo(parseInt(el.dataset.index, 10));
        });
    });
    const current = list.querySelector(".move-item.current");
    if (current) current.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

function coordLabel(x, y, size) {
    return String.fromCharCode(65 + x) + String(size - y);
}

function renderControls() {
    $("btnBack").disabled = State.viewIndex <= 0 || State.thinking;
    $("btnForward").disabled = State.viewIndex >= State.totalMoves || State.thinking;
    const canAiMove = !State.gameOver && !State.thinking;
    $("btnAiMove").disabled = !canAiMove;

    document.querySelectorAll("#ruleControl button").forEach((b) => {
        b.classList.toggle("active", parseInt(b.dataset.rule) === State.rule);
    });
    document.querySelectorAll("#colorControl button").forEach((b) => {
        b.classList.toggle("active", parseInt(b.dataset.color) === State.playerColor);
    });
    document.querySelectorAll("#sizeControl button").forEach((b) => {
        b.classList.toggle("active", parseInt(b.dataset.size) === State.boardSize);
    });
    document.querySelectorAll("#modeControl button").forEach((b) => {
        b.classList.toggle("active", b.dataset.mode === State.gameMode);
    });

    const colorField = $("colorField");
    if (colorField) {
        colorField.style.display = State.gameMode === "pvp" ? "none" : "";
    }
}

function renderRuleHint() {
    $("ruleHint").textContent = RULE_INFO[State.rule]?.desc || "";
    $("modeHint").textContent = State.gameMode === "pve" ? "人机：AI 自动应招" : "双人：玩家轮流扮演黑白";
}

function setThinking(v) {
    // pvp 模式永远不显示思考状态
    if (State.gameMode === "pvp") v = false;
    // 游戏结束时不显示思考
    if (State.gameOver) v = false;
    State.thinking = v;
    renderControls();
    if (v) {
        setHint("引擎思考中…", "warn");
    } else if (State.gameOver) {
        const winText = State.winner === 1 ? "黑棋胜" : State.winner === 2 ? "白棋胜" : "平局";
        setHint("游戏结束 - " + winText);
    } else {
        setHint("点击棋盘交叉点选择落子，再次点击确认");
    }
}

function setHint(text, type) {
    const el = $("hintBar");
    $("hintText").textContent = text;
    el.classList.remove("warn");
    if (type) el.classList.add(type);
}

// ============= 控件事件 =============
document.querySelectorAll("#modeControl button").forEach((b) => {
    b.addEventListener("click", () => {
        document.querySelectorAll("#modeControl button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        const mode = b.dataset.mode;
        $("modeHint").textContent = mode === "pve" ? "人机：AI 自动应招" : "双人：玩家轮流扮演黑白";
        const colorField = $("colorField");
        if (colorField) colorField.style.display = mode === "pvp" ? "none" : "";
    });
});

document.querySelectorAll("#ruleControl button").forEach((b) => {
    b.addEventListener("click", () => {
        document.querySelectorAll("#ruleControl button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        const rule = parseInt(b.dataset.rule);
        $("ruleHint").textContent = RULE_INFO[rule]?.desc || "";
    });
});

document.querySelectorAll("#colorControl button").forEach((b) => {
    b.addEventListener("click", () => {
        document.querySelectorAll("#colorControl button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
    });
});

document.querySelectorAll("#sizeControl button").forEach((b) => {
    b.addEventListener("click", () => {
        document.querySelectorAll("#sizeControl button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
    });
});

$("btnNewGame").addEventListener("click", async () => {
    const rule = parseInt(document.querySelector("#ruleControl button.active").dataset.rule);
    const playerColor = parseInt(document.querySelector("#colorControl button.active").dataset.color);
    const boardSize = parseInt(document.querySelector("#sizeControl button.active").dataset.size);
    const gameMode = document.querySelector("#modeControl button.active").dataset.mode;

    setThinking(true);
    try {
        const res = await API.post("/api/new_game", {
            rule, player_color: playerColor, board_size: boardSize, game_mode: gameMode
        });
        if (res.ok) {
            updateFromServer(res.data);
            toast(`新对局：${RULE_INFO[rule].name} · ${gameMode === "pve" ? "人机" : "双人"}`, "success");
        } else {
            toast(res.error || "新对局失败", "error");
        }
    } catch (err) {
        toast("网络错误: " + err.message, "error");
    } finally {
        setThinking(false);
    }
});

$("btnBack").addEventListener("click", async () => {
    const res = await API.post("/api/undo", {});
    if (res.ok) updateFromServer(res.data);
});

$("btnForward").addEventListener("click", async () => {
    const res = await API.post("/api/redo", {});
    if (res.ok) updateFromServer(res.data);
});

$("btnAiMove").addEventListener("click", async () => {
    if (State.thinking) return;
    setThinking(true);
    try {
        const res = await API.post("/api/ai_move", {});
        if (res.ok) {
            updateFromServer(res.data);
        } else {
            toast(res.error || "AI 下子失败", "error");
        }
    } catch (err) {
        toast("网络错误: " + err.message, "error");
    } finally {
        setThinking(false);
    }
});

async function jumpTo(index) {
    const res = await API.post("/api/jump", { index });
    if (res.ok) updateFromServer(res.data);
}

// ============= 抽屉开关 =============
function openDrawer() {
    $("drawer").classList.add("open");
    $("drawerBackdrop").classList.remove("hidden");
}
function closeDrawer() {
    $("drawer").classList.remove("open");
    $("drawerBackdrop").classList.add("hidden");
}
$("btnDrawer").addEventListener("click", openDrawer);
$("btnCloseDrawer").addEventListener("click", closeDrawer);
$("drawerBackdrop").addEventListener("click", closeDrawer);

// ============= 设置弹窗 =============
$("btnSettings").addEventListener("click", async () => {
    const res = await API.get("/api/config");
    if (res.ok) {
        $("cfgTimeout").value = res.data.timeout_turn;
        $("cfgThreads").value = res.data.thread_num;
        $("cfgMemory").value = res.data.max_memory;
        $("cfgEngineInfo").textContent =
            `引擎: ${res.data.engine_path || "未启动"}\n` +
            `架构: ${res.data.engine_arch_label || "未启动"}\n` +
            `平台: ${res.data.platform} ${res.data.arch}\n` +
            `规则: ${RULE_INFO[res.data.rule]?.name || res.data.rule_name}\n` +
            `状态: ${res.data.started ? "已启动" : "未启动"}` +
            (res.data.start_error ? `\n错误: ${res.data.start_error}` : "");
    }
    $("settingsModal").classList.remove("hidden");
});

$("closeSettings").addEventListener("click", () => $("settingsModal").classList.add("hidden"));
$("cancelSettings").addEventListener("click", () => $("settingsModal").classList.add("hidden"));
$("settingsModal").addEventListener("click", (e) => {
    if (e.target === $("settingsModal")) $("settingsModal").classList.add("hidden");
});

$("saveSettings").addEventListener("click", async () => {
    const timeout = parseInt($("cfgTimeout").value);
    const threads = parseInt($("cfgThreads").value);
    const memory = parseInt($("cfgMemory").value);
    const res = await API.post("/api/config", {
        timeout_turn: timeout, thread_num: threads, max_memory: memory,
    });
    if (res.ok) {
        toast("设置已保存", "success");
        $("settingsModal").classList.add("hidden");
    } else {
        toast(res.error || "保存失败", "error");
    }
});

// ============= 轮询 =============
async function pollState() {
    // 始终轮询，确保状态同步
    try {
        const res = await API.get("/api/state");
        if (res.ok) {
            const prevThinking = State.thinking;
            updateFromServer(res.data);
            // 如果服务端 thinking 变为 false 但前端还显示思考中，强制更新
            if (prevThinking && !State.thinking) {
                setThinking(false);
            }
        }
    } catch (e) {}
}
setInterval(pollState, 1000);

// ============= Toast =============
let toastTimer = null;
function toast(msg, type) {
    const el = $("toast");
    el.textContent = msg;
    el.className = "toast";
    if (type) el.classList.add(type);
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.add("hidden"), 2500);
}

// ============= 初始化 =============
window.addEventListener("resize", resizeCanvas);

async function init() {
    try {
        const res = await API.get("/api/state");
        if (res.ok) updateFromServer(res.data);
    } catch (e) {
        toast("无法连接服务器", "error");
    }
    resizeCanvas();
    renderAll();
}

init();
