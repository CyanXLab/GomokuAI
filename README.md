# GomokuPrime

> 基于 [RapFi](https://github.com/dhbloo/rapfi) 引擎的五子棋桌面应用 · Flask + Fluent UI

[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![Engine](https://img.shields.io/badge/engine-RapFi%200.43.01-orange.svg)](https://github.com/dhbloo/rapfi)
[![Platform](https://img.shields.io/badge/platform-Win%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](#跨平台)

## 🎯 项目简介

GomokuPrime 是一个基于 RapFi 引擎的五子棋桌面应用，拥有**职业级 AI 棋力**。引擎搜索深度可达 **30+ 层**，每秒评估 **38 万+ 节点**，能找到 **33 步必胜路线**（+M33）。

### 🤖 AI 实力验证

```
搜索深度:  30 层（迭代加深）
思考时间:  7.8 秒（完整利用）
节点数:    297 万
速度:      381K 节点/秒
必胜路线:  +M33（找到 33 步必胜）
```

## ✨ 核心特性

### 引擎（最强配置）

| 功能 | 说明 |
|------|------|
| **定式开局** | 天元开局（无禁手必胜），支持 Swap1/Swap2 |
| **VCF 搜索** | Victory by Continuous Four，连续冲四必胜搜索 |
| **VCT 搜索** | Victory by Continuous Threat，连续活三威胁搜索 |
| **神经网络评估器** | mix9svq（9 点混合标量量化），SIMD 加速 |
| **棋型评分** | 8 种棋型识别（五连/活四/冲四/活三/眠三/活二/眠二/无） |
| **置换表** | 128MB Zobrist 哈希表 |
| **AlphaBeta 搜索** | Aspiration Window + Null Move + Killer Move + History Heuristic |
| **迭代加深** | 搜索深度 30+ 层 |
| **YixinDB 数据库** | 自动学习必胜/必败路线 |
| **多线程** | 自动使用所有 CPU 核心 |
| **最大强度** | strength 100（满级） |

### 游戏模式

- **人机模式（PvE）**：AI 自动应招，8 秒深度思考
- **双人模式（PvP）**：玩家轮流扮演黑白，AI 不干预
- **无回合限制**：回退后可改变身份下子
- **游戏结束可继续**：连五后回退即可重新下子

### 三种规则

| 规则 | 说明 | 模型 |
|------|------|------|
| 自由规则 | 无禁手，五连或长连均胜 | `mix9svqfreestyle_bsmix.bin.lz4` |
| 标准规则 | 无禁手，有三三/四四限制 | `mix9svqstandard_bs15.bin.lz4` |
| 连珠规则 | 黑棋禁手，黑/白模型分开 | `mix9svqrenju_bs15_black/white.bin.lz4` |

### 界面

- **Fluent UI 深色主题**：Mica 材质背景、圆角、柔和阴影
- **棋子序号**：每步棋标注顺序数字
- **两次点击确认**：防止误触
- **抽屉式面板**：可折叠侧边栏
- **响应式布局**：桌面/平板/手机自适应
- **防缓存**：每次加载最新代码
- **调试日志**：后端实时输出引擎思考过程

## 🚀 快速开始

### 依赖

- Python 3.8+
- Flask（首次运行自动安装）

### Windows

```bat
双击 run.bat
```

### Linux / macOS

```bash
chmod +x run.sh
./run.sh
```

启动后浏览器自动打开 `http://127.0.0.1:18080`

## 📖 使用说明

### 基本操作

| 操作 | 说明 |
|------|------|
| **下子** | 点击棋盘交叉点 → 再次点击确认（防误触） |
| **取消预览** | 右键 或 ESC |
| **后退/前进** | 棋盘下方按钮 或 键盘 ← → |
| **AI 下子** | 点击"AI下子"让 AI 替当前回合下 |
| **开新对局** | 右上角面板图标 → 选择参数 → 开始 |

### 棋子序号

每个棋子中间显示步数序号：
- 黑棋上显示白色数字
- 白棋上显示黑色数字

### 调试日志

后端控制台实时输出：
```
[NEW_GAME] rule=0, size=15, color=1, mode=pve
[MOVE] 玩家请求下子 (7,7), mode=pve
[ENGINE] think: 1 moves, engine_color=2
  [ENGINE] MESSAGE Depth 20-28 | Eval -487 | Time 6208ms
  [ENGINE] MESSAGE Speed 211K | Depth 20-24 | Node 1685K | Time 7973ms
[ENGINE] 返回: (6,6)
[MOVE] AI 返回: (6,6)
```

## 📁 项目结构

```
GomokuPrime/
├── run.py                  # 跨平台启动入口
├── run.bat / run.sh        # 启动脚本
├── server.py               # Flask 后端（API + 游戏逻辑 + 调试日志）
├── engine_manager.py       # RapFi 引擎封装（跨平台 + 失败回退）
├── game_state.py           # 游戏状态管理（PvE/PvP，RLock 线程安全）
├── config.json             # 应用配置
├── requirements.txt        # Python 依赖
├── .gitignore
├── static/
│   ├── index.html          # 主页面（Fluent UI v3.0）
│   ├── css/style.css       # 深色主题样式
│   └── js/main.js          # 前端逻辑
└── engine/                 # RapFi 引擎与模型
    ├── config.toml         # 引擎配置（最强参数）
    ├── pbrain-rapfi-*      # 多平台引擎二进制
    └── mix9svq*.bin.lz4    # 神经网络模型
```

## 🔧 引擎工作原理

### 搜索流程

```
玩家下子 → BOARD 命令传入局面
    ↓
probeOpening() 定式探测
    ├─ 命中 → 直接返回定式着法
    └─ 未命中 → 进入主搜索
         ↓
    iterativeDeepingLoop() 迭代加深
         ├─ Depth 2 → 4 → 6 → ... → 30+
         ├─ aspirationSearch() 渴望窗口搜索
         │    └─ search() AlphaBeta 递归
         │         ├─ 置换表 probe()
         │         ├─ Null Move 剪枝
         │         ├─ Killer Move 优先
         │         ├─ VCF/VCT 着法生成
         │         └─ mix9svq 评估器
         └─ 时间到 → 返回最佳着法
```

### VCF/VCT 搜索

- **VCF**：连续冲四必胜搜索（`vcfsearch`/`vcfdefend`）
- **VCT**：连续活三威胁必胜搜索
- 在搜索深度 ≤ 0 时自动触发

### 关键修复

| 问题 | 原因 | 修复 |
|------|------|------|
| AI 极弱 | `max_memory` 单位错误（MB 当字节） | 转换为字节 `MB * 1024 * 1024` |
| 连五卡住 | `Lock` 不可重入，`to_dict` 死锁 | 改用 `RLock` |
| pvp 显示思考 | 前端 pvp 也设 thinking | pvp 模式强制 `thinking=false` |

## 🌐 HTTP API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/state` | 获取游戏状态 |
| GET | `/api/config` | 获取引擎配置 |
| GET | `/api/rules` | 获取规则列表 |
| POST | `/api/new_game` | 开始新对局 |
| POST | `/api/move` | 玩家下子 |
| POST | `/api/ai_move` | AI 下子 |
| POST | `/api/undo` | 后退 |
| POST | `/api/redo` | 前进 |
| POST | `/api/jump` | 跳转 |
| POST | `/api/config` | 更新配置 |

## 🖥️ 跨平台

| 平台 | 架构 | 引擎 |
|------|------|------|
| Windows | x86_64 | AVX-VNNI / AVX2 / SSE |
| Linux | x86_64 | AVX-VNNI / AVX2 / SSE |
| macOS | Apple Silicon | 原生支持 |

## 📦 配置说明

### `config.json`（应用配置）

```json
{
    "engine": {
        "architecture": "auto",
        "max_memory_mb": 512,
        "thread_num": 0,
        "timeout_turn_ms": 8000
    },
    "game": { "mode": "pve" }
}
```

### `engine/config.toml`（引擎配置）

- 置换表 128MB
- 最大搜索深度 200
- 数据库启用
- Aspiration Window 启用
- 多线程自动

## 🙏 致谢

- **引擎**：[RapFi](https://github.com/dhbloo/rapfi) by dhbloo
- **模型**：mix9svq 神经网络
- **设计**：Microsoft Fluent UI / Windows 11

## 📄 License

GPL-3.0（继承自 RapFi 引擎）
