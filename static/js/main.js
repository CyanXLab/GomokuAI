/**
 * GomokuPrime v5.0
 */
const API = {
    async get(path) { const r = await fetch(path); return r.json(); },
    async post(path, body) {
        const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
        return r.json();
    },
};

const State = {
    rule: 0, boardSize: 15, board: [], moves: [], totalMoves: 0, viewIndex: 0,
    currentColor: 1, playerColor: 1, gameMode: "pve",
    gameOver: false, winner: 0, thinking: false,
    pendingMove: null, hoverPos: null, evalHistory: [],
    showEval: true,
};

const RULE_INFO = {
    0: { name: "自由", desc: "无禁手，五连或长连均胜。黑棋天元开局必胜。" },
    1: { name: "标准", desc: "无禁手，但有三三、四四等基础限制。" },
    2: { name: "连珠", desc: "黑棋有三三、四四、长连禁手。黑/白模型分开。" },
};

const $ = (id) => document.getElementById(id);
const canvas = $("board");
const ctx = canvas.getContext("2d");
const evalCanvas = $("evalChart");
const evalCtx = evalCanvas.getContext("2d");

// ============= 棋盘渲染 =============
function resizeCanvas() {
    const wrapper = canvas.parentElement;
    const rect = wrapper.getBoundingClientRect();
    const size = Math.max(280, Math.min(rect.width - 16, rect.height - 16));
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

    const grad = ctx.createLinearGradient(0, 0, cssW, cssW);
    grad.addColorStop(0, "#d4a368"); grad.addColorStop(0.5, "#c8965a"); grad.addColorStop(1, "#b8854a");
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, cssW, cssW);

    const innerGrad = ctx.createRadialGradient(cssW/2, cssW/2, cssW*0.3, cssW/2, cssW/2, cssW*0.7);
    innerGrad.addColorStop(0, "rgba(0,0,0,0)"); innerGrad.addColorStop(1, "rgba(0,0,0,0.2)");
    ctx.fillStyle = innerGrad;
    ctx.fillRect(0, 0, cssW, cssW);

    ctx.strokeStyle = "rgba(70, 40, 20, 0.85)"; ctx.lineWidth = 1;
    for (let i = 0; i < size; i++) {
        const p = padding + i * cellSize;
        ctx.beginPath(); ctx.moveTo(padding, p); ctx.lineTo(cssW - padding, p); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(p, padding); ctx.lineTo(p, cssW - padding); ctx.stroke();
    }
    ctx.strokeStyle = "rgba(70, 40, 20, 1)"; ctx.lineWidth = 2;
    ctx.strokeRect(padding, padding, cssW - padding*2, cssW - padding*2);

    const stars = getStarPoints(size);
    ctx.fillStyle = "rgba(70, 40, 20, 0.9)";
    for (const [sx, sy] of stars) {
        ctx.beginPath();
        ctx.arc(padding + sx*cellSize, padding + sy*cellSize, Math.max(2.5, cellSize*0.07), 0, Math.PI*2);
        ctx.fill();
    }

    ctx.fillStyle = "rgba(70, 40, 20, 0.7)";
    ctx.font = `${Math.max(9, cellSize*0.22)}px sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    for (let i = 0; i < size; i++) {
        const p = padding + i * cellSize;
        ctx.fillText(String.fromCharCode(65 + i), p, padding * 0.5);
        ctx.fillText(String(size - i), padding * 0.5, p);
    }

    const visibleMoves = State.moves.slice(0, State.viewIndex);
    for (let i = 0; i < visibleMoves.length; i++) {
        const m = visibleMoves[i];
        drawStone(m.x, m.y, m.color, cellSize, padding, false);
        drawMoveNumber(m.x, m.y, m.color, i + 1, cellSize, padding);
    }

    if (State.viewIndex > 0) {
        const last = State.moves[State.viewIndex - 1];
        const px = padding + last.x * cellSize;
        const py = padding + last.y * cellSize;
        ctx.strokeStyle = "#ff4d6d"; ctx.lineWidth = 2.5;
        ctx.beginPath(); ctx.arc(px, py, cellSize * 0.16, 0, Math.PI * 2); ctx.stroke();
    }

    if (State.pendingMove) {
        const { x, y } = State.pendingMove;
        drawStone(x, y, State.currentColor, cellSize, padding, true);
        const px = padding + x * cellSize; const py = padding + y * cellSize;
        ctx.strokeStyle = "#fbbf24"; ctx.lineWidth = 2.5; ctx.setLineDash([5, 4]);
        ctx.beginPath(); ctx.arc(px, py, cellSize * 0.46, 0, Math.PI * 2); ctx.stroke();
        ctx.setLineDash([]);
    } else if (State.hoverPos && !State.gameOver && !State.thinking) {
        const { x, y } = State.hoverPos;
        if (State.board[x] && State.board[x][y] === 0) {
            drawStone(x, y, State.currentColor, cellSize, padding, true);
        }
    }
}

function drawStone(x, y, color, cellSize, padding, preview) {
    const px = padding + x * cellSize; const py = padding + y * cellSize;
    const r = cellSize * 0.43;
    ctx.save();
    if (preview) ctx.globalAlpha = 0.5;
    ctx.shadowColor = "rgba(0,0,0,0.55)"; ctx.shadowBlur = 5; ctx.shadowOffsetX = 1; ctx.shadowOffsetY = 2;
    const grad = ctx.createRadialGradient(px - r*0.35, py - r*0.35, r*0.1, px, py, r);
    if (color === 1) { grad.addColorStop(0, "#6a6a6a"); grad.addColorStop(0.5, "#2a2a2a"); grad.addColorStop(1, "#050505"); }
    else { grad.addColorStop(0, "#ffffff"); grad.addColorStop(0.5, "#f0f0f0"); grad.addColorStop(1, "#b0b0b0"); }
    ctx.fillStyle = grad;
    ctx.beginPath(); ctx.arc(px, py, r, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
}

function drawMoveNumber(x, y, color, num, cellSize, padding) {
    const px = padding + x * cellSize; const py = padding + y * cellSize;
    const fontSize = Math.max(10, cellSize * 0.32);
    ctx.save();
    ctx.font = `bold ${fontSize}px sans-serif`;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
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

// ============= 评估曲线 =============
function drawEvalChart() {
    const w = evalCanvas.width; const h = evalCanvas.height;
    evalCtx.clearRect(0, 0, w, h);
    evalCtx.strokeStyle = "rgba(255,255,255,0.05)"; evalCtx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) { const y = (h / 4) * i; evalCtx.beginPath(); evalCtx.moveTo(0, y); evalCtx.lineTo(w, y); evalCtx.stroke(); }
    evalCtx.strokeStyle = "rgba(255,255,255,0.15)";
    evalCtx.beginPath(); evalCtx.moveTo(0, h/2); evalCtx.lineTo(w, h/2); evalCtx.stroke();

    const history = State.evalHistory || [];
    if (history.length < 2) {
        evalCtx.fillStyle = "rgba(255,255,255,0.3)";
        evalCtx.font = "11px sans-serif"; evalCtx.textAlign = "center";
        evalCtx.fillText("暂无评估数据", w/2, h/2);
        return;
    }
    const maxVal = 1000;
    const step = w / Math.max(history.length - 1, 1);

    evalCtx.strokeStyle = "#60a5fa"; evalCtx.lineWidth = 2; evalCtx.beginPath();
    for (let i = 0; i < history.length; i++) {
        const x = i * step; const v = history[i].black || 0;
        const y = h/2 - (v / maxVal) * (h/2 - 5);
        if (i === 0) evalCtx.moveTo(x, y); else evalCtx.lineTo(x, y);
    }
    evalCtx.stroke();

    evalCtx.strokeStyle = "#4ade80"; evalCtx.lineWidth = 2; evalCtx.beginPath();
    for (let i = 0; i < history.length; i++) {
        const x = i * step; const v = history[i].white || 0;
        const y = h/2 - (v / maxVal) * (h/2 - 5);
        if (i === 0) evalCtx.moveTo(x, y); else evalCtx.lineTo(x, y);
    }
    evalCtx.stroke();

    if (State.viewIndex > 0 && State.viewIndex <= history.length) {
        const x = (State.viewIndex - 1) * step;
        evalCtx.strokeStyle = "#ff4d6d"; evalCtx.lineWidth = 1.5; evalCtx.setLineDash([3, 3]);
        evalCtx.beginPath(); evalCtx.moveTo(x, 0); evalCtx.lineTo(x, h); evalCtx.stroke();
        evalCtx.setLineDash([]);
    }
}

// ============= 鼠标事件 =============
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
    if (cell && (!State.hoverPos || State.hoverPos.x !== cell.x || State.hoverPos.y !== cell.y)) { State.hoverPos = cell; drawBoard(); }
    else if (!cell && State.hoverPos) { State.hoverPos = null; drawBoard(); }
});
canvas.addEventListener("mouseleave", () => { State.hoverPos = null; drawBoard(); });
canvas.addEventListener("click", handleBoardClick);

function handleBoardClick(e) {
    if (State.thinking) { toast("引擎思考中", "error"); return; }
    const rect = canvas.getBoundingClientRect();
    const cell = pixelToCell(e.clientX - rect.left, e.clientY - rect.top);
    if (!cell) return;
    if (State.board[cell.x][cell.y] !== 0) { toast("该位置已有棋子", "error"); State.pendingMove = null; drawBoard(); return; }
    if (State.pendingMove && State.pendingMove.x === cell.x && State.pendingMove.y === cell.y) {
        const move = State.pendingMove; State.pendingMove = null; confirmMove(move.x, move.y);
    } else {
        State.pendingMove = cell;
        if (State.viewIndex < State.totalMoves) setHint("再次点击确认（从此步开始新对局）", "warn");
        else setHint("再次点击同一位置确认", "warn");
        drawBoard();
    }
}

canvas.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    if (State.pendingMove) { State.pendingMove = null; setHint("点击棋盘交叉点，再次点击确认"); drawBoard(); }
});

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && State.pendingMove) { State.pendingMove = null; setHint("点击棋盘交叉点，再次点击确认"); drawBoard(); }
    if (e.key === "ArrowLeft") $("btnBack").click();
    if (e.key === "ArrowRight") $("btnForward").click();
});

async function confirmMove(x, y) {
    const isPvp = State.gameMode === "pvp";
    if (!isPvp) setThinking(true);
    try {
        const res = await API.post("/api/move", { x, y });
        if (res.ok) updateFromServer(res.data);
        else toast(res.error || "下子失败", "error");
    } catch (err) { toast("网络错误: " + err.message, "error"); }
    finally { if (!isPvp) setThinking(false); }
}

// ============= UI 更新 =============
function updateFromServer(data) {
    State.rule = data.rule;
    State.boardSize = data.board_size;
    State.board = data.board;
    State.moves = data.moves;
    State.totalMoves = data.total_moves;
    State.viewIndex = data.view_index;
    State.currentColor = data.current_color;
    State.playerColor = data.player_color;
    State.gameMode = data.game_mode;
    State.gameOver = data.game_over;
    State.winner = data.winner;
    State.thinking = data.thinking;
    State.evalHistory = data.eval_history || [];
    renderAll();
}

function renderAll() {
    drawBoard();
    if (State.showEval) drawEvalChart();
    renderStatusTag();
    renderMoveList();
    renderButtonStates();
    renderRuleHint();
}

function renderStatusTag() {
    const ruleName = RULE_INFO[State.rule]?.name || "未知";
    const turn = State.gameOver ? (State.winner === 1 ? "黑胜" : State.winner === 2 ? "白胜" : "平局") : (State.currentColor === 1 ? "黑棋" : "白棋");
    const mode = State.gameMode === "pve" ? "人机" : "双人";
    $("statusTag").textContent = `${ruleName} · ${turn} · ${State.viewIndex}/${State.totalMoves} · ${mode}`;
}

function renderMoveList() {
    const list = $("moveList");
    if (State.moves.length === 0) { list.innerHTML = '<div class="empty-hint">尚未开始对局</div>'; return; }
    let html = "";
    for (let i = 0; i < State.moves.length; i++) {
        const m = State.moves[i];
        const coord = String.fromCharCode(65 + m.x) + String(State.boardSize - m.y);
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
        el.addEventListener("click", () => jumpTo(parseInt(el.dataset.index, 10)));
    });
    const current = list.querySelector(".move-item.current");
    if (current) current.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

// 关键修复：renderButtonStates 只更新按钮的 disabled 状态，不覆盖 active
function renderButtonStates() {
    $("btnBack").disabled = State.viewIndex <= 0 || State.thinking;
    $("btnForward").disabled = State.viewIndex >= State.totalMoves || State.thinking;
    $("btnAiMove").disabled = State.gameOver || State.thinking;
    // 注意：不覆盖 segmented 按钮的 active 状态，避免用户选择被重置
    // 只更新 colorField 显示
    const colorField = $("colorField");
    if (colorField) colorField.style.display = State.gameMode === "pvp" ? "none" : "";
}

function renderRuleHint() {
    $("ruleHint").textContent = RULE_INFO[State.rule]?.desc || "";
}

function setThinking(v) {
    if (State.gameMode === "pvp") v = false;
    if (State.gameOver) v = false;
    State.thinking = v;
    renderButtonStates();
    if (v) setHint("引擎思考中…", "warn");
    else if (State.gameOver) {
        const wt = State.winner === 1 ? "黑棋胜" : State.winner === 2 ? "白棋胜" : "平局";
        setHint("游戏结束 - " + wt);
    } else setHint("点击棋盘交叉点，再次点击确认");
}

function setHint(text, type) {
    const el = $("hintBar");
    $("hintText").textContent = text;
    el.classList.remove("warn");
    if (type) el.classList.add(type);
}

// ============= 控件事件（只更新 UI，不同步服务端）=============
document.querySelectorAll("#modeControl button").forEach((b) => {
    b.addEventListener("click", () => {
        document.querySelectorAll("#modeControl button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        const mode = b.dataset.mode;
        State.gameMode = mode;  // 立即更新本地状态
        $("colorField").style.display = mode === "pvp" ? "none" : "";
        renderStatusTag();  // 刷新状态标签
    });
});
document.querySelectorAll("#ruleControl button").forEach((b) => {
    b.addEventListener("click", () => {
        document.querySelectorAll("#ruleControl button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        const rule = parseInt(b.dataset.rule);
        State.rule = rule;  // 立即更新本地状态
        $("ruleHint").textContent = RULE_INFO[rule]?.desc || "";
        renderStatusTag();  // 刷新状态标签
    });
});
document.querySelectorAll("#sizeControl button").forEach((b) => {
    b.addEventListener("click", () => {
        document.querySelectorAll("#sizeControl button").forEach((x) => x.classList.remove("active"));
        b.classList.add("active");
        State.boardSize = parseInt(b.dataset.size);  // 立即更新
        renderStatusTag();
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

// 评估曲线开关
$("evalToggle").addEventListener("change", (e) => {
    State.showEval = e.target.checked;
    $("evalBody").style.display = State.showEval ? "" : "none";
});

$("btnNewGame").addEventListener("click", async () => {
    const rule = parseInt(document.querySelector("#ruleControl button.active").dataset.rule);
    const playerColor = parseInt(document.querySelector("#colorControl button.active").dataset.color);
    const boardSize = parseInt(document.querySelector("#sizeControl button.active").dataset.size);
    const gameMode = document.querySelector("#modeControl button.active").dataset.mode;
    setThinking(true);
    try {
        const res = await API.post("/api/new_game", { rule, player_color: playerColor, board_size: boardSize, game_mode: gameMode });
        if (res.ok) {
            updateFromServer(res.data);
            // 新对局后同步按钮状态
            document.querySelectorAll("#ruleControl button").forEach((b) => { b.classList.toggle("active", parseInt(b.dataset.rule) === rule); });
            document.querySelectorAll("#colorControl button").forEach((b) => { b.classList.toggle("active", parseInt(b.dataset.color) === playerColor); });
            document.querySelectorAll("#sizeControl button").forEach((b) => { b.classList.toggle("active", parseInt(b.dataset.size) === boardSize); });
            document.querySelectorAll("#modeControl button").forEach((b) => { b.classList.toggle("active", b.dataset.mode === gameMode); });
            toast(`新对局：${RULE_INFO[rule].name} · ${gameMode === "pve" ? "人机" : "双人"}`, "success");
        } else toast(res.error || "新对局失败", "error");
    } catch (err) { toast("网络错误: " + err.message, "error"); }
    finally { setThinking(false); }
});

$("btnBack").addEventListener("click", async () => { const res = await API.post("/api/undo", {}); if (res.ok) updateFromServer(res.data); });
$("btnForward").addEventListener("click", async () => { const res = await API.post("/api/redo", {}); if (res.ok) updateFromServer(res.data); });
$("btnAiMove").addEventListener("click", async () => {
    if (State.thinking) return;
    setThinking(true);
    try {
        const res = await API.post("/api/ai_move", {});
        if (res.ok) updateFromServer(res.data);
        else toast(res.error || "AI 下子失败", "error");
    } catch (err) { toast("网络错误: " + err.message, "error"); }
    finally { setThinking(false); }
});

async function jumpTo(index) { const res = await API.post("/api/jump", { index }); if (res.ok) updateFromServer(res.data); }

// ============= 引擎参数页面 =============
async function loadEnginesForSettings() {
    try {
        const res = await API.get("/api/engines");
        if (res.ok) {
            const select = $("cfgArch");
            const current = select.value || "auto";
            select.innerHTML = '<option value="auto">自动选择</option>';
            res.data.engines.filter(e => e.available).forEach(e => {
                const opt = document.createElement("option");
                opt.value = e.arch;
                opt.textContent = e.arch_label;
                select.appendChild(opt);
            });
            select.value = current;
        }
    } catch (e) {}
}

$("btnSettings").addEventListener("click", async () => {
    await loadEnginesForSettings();
    const res = await API.get("/api/config");
    if (res.ok) {
        $("cfgTimeout").value = res.data.timeout_turn;
        $("cfgThreads").value = res.data.thread_num;
        $("cfgMemory").value = res.data.max_memory;
        $("cfgArch").value = res.data.arch_setting || "auto";
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
$("settingsModal").addEventListener("click", (e) => { if (e.target === $("settingsModal")) $("settingsModal").classList.add("hidden"); });

$("saveSettings").addEventListener("click", async () => {
    const res = await API.post("/api/config", {
        timeout_turn: parseInt($("cfgTimeout").value),
        thread_num: parseInt($("cfgThreads").value),
        max_memory: parseInt($("cfgMemory").value),
    });
    if (res.ok) {
        // 切换架构
        const arch = $("cfgArch").value;
        if (arch && arch !== "auto") {
            await API.post("/api/architecture", { arch });
        }
        toast("参数已保存", "success");
        $("settingsModal").classList.add("hidden");
    } else toast(res.error || "保存失败", "error");
});

// ============= 轮询 =============
async function pollState() {
    try {
        const res = await API.get("/api/state");
        if (res.ok) {
            const prevThinking = State.thinking;
            updateFromServer(res.data);
            if (prevThinking && !State.thinking) setThinking(false);
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
window.addEventListener("resize", () => { resizeCanvas(); if (State.showEval) drawEvalChart(); });

async function init() {
    try {
        const res = await API.get("/api/state");
        if (res.ok) updateFromServer(res.data);
    } catch (e) { toast("无法连接服务器", "error"); }
    resizeCanvas();
    const evalRect = evalCanvas.getBoundingClientRect();
    evalCanvas.width = evalRect.width;
    evalCanvas.height = 120;
    renderAll();
}
init();
