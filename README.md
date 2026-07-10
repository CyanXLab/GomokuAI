# GomokuPrime

基于 [RapFi](https://github.com/dhbloo/rapfi) 引擎的五子棋桌面应用，使用 **Flask + HTML/CSS/JS** 构建，前端采用 **Fluent UI / Windows 11** 设计风格。

## ✨ 特性

### 🤖 引擎（最强配置）

本项目启用了 RapFi 引擎的所有高级搜索功能：

| 功能 | 说明 |
|------|------|
| **定式开局** | 天元开局（无禁手必胜），支持 Swap1/Swap2 |
| **VCF 搜索** | Victory by Continuous Four，连续冲四必胜搜索 |
| **VCT 搜索** | Victory by Continuous Threat，连续活三威胁搜索 |
| **神经网络评估器** | mix9svq（9 点混合标量量化），30 万+ 节点/秒 |
| **棋型评分** | 8 种棋型识别（五连/活四/冲四/活三/眠三/活二/眠二/无） |
| **置换表** | 256MB Zobrist 哈希表 |
| **AlphaBeta 搜索** | Aspiration Window + Null Move + Killer Move + History Heuristic |
| **迭代加深** | 搜索深度可达 30+ 层 |
| **YixinDB 数据库** | 自动学习必胜/必败路线，越下越强 |
| **多线程** | 自动使用所有 CPU 核心 |
| **最大强度** | strength 100（满级） |

### 🎮 游戏模式

- **人机模式（PvE）**：玩家下子后 AI 自动应招
- **双人模式（PvP）**：玩家轮流扮演黑白，AI 不干预
- **无回合限制**：回退后可改变身份下子，游戏结束后可继续

### 📐 三种规则

| 规则 | 说明 | 模型 |
|------|------|------|
| 自由规则 | 无禁手，五连或长连均胜 | `mix9svqfreestyle_bsmix.bin.lz4` |
| 标准规则 | 无禁手，有三三/四四限制 | `mix9svqstandard_bs15.bin.lz4` |
| 连珠规则 | 黑棋禁手，黑/白模型分开 | `mix9svqrenju_bs15_black/white.bin.lz4` |

### 🖥️ 跨平台

| 平台 | 架构 | 引擎 |
|------|------|------|
| Windows | x86_64 | AVX-VNNI / AVX2 / SSE |
| Linux | x86_64 | AVX-VNNI / AVX2 / SSE |
| Linux | ARM64 | NEON（需自行编译） |
| macOS | Apple Silicon | 原生支持 |

### 🎨 界面

- **Fluent UI 深色主题**：Mica 材质背景、圆角、柔和阴影
- **棋子序号**：每步棋标注顺序数字
- **两次点击确认**：防止误触
- **抽屉式面板**：可折叠侧边栏
- **响应式布局**：自适应桌面/平板/手机
- **防缓存**：每次加载最新代码

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

1. **开始新对局**：点击右上角面板图标 → 选择模式/规则/执子 → 点击"开始新对局"
2. **下子**：点击棋盘交叉点 → 再次点击同一位置确认（防误触）
3. **取消预览**：右键点击 或 按 ESC
4. **后退/前进**：棋盘下方按钮 或 键盘 ← →
5. **AI 下子**：点击"AI下子"按钮让 AI 替当前回合下子

### 棋子序号

每个棋子中间显示步数序号：
- 黑棋上显示白色数字
- 白棋上显示黑色数字

### 游戏模式

- **人机模式**：选择执黑或执白，AI 自动应招
- **双人模式**：两位玩家轮流下子，AI 不参与
- 两种模式都支持：前进/后退、AI 下一步、走子历史跳转

### 引擎设置

点击右上角齿轮图标：
- 单步思考时间（毫秒，建议 5000-15000）
- 线程数（0=自动使用所有核心）
- 最大内存（MB，置换表大小）

## 📁 项目结构

```
GomokuPrime/
├── run.py                  # 跨平台启动入口
├── run.bat                 # Windows 启动脚本
├── run.sh                  # Linux/macOS 启动脚本
├── server.py               # Flask 后端（API + 游戏逻辑）
├── engine_manager.py       # RapFi 引擎封装（跨平台 + 失败回退）
├── game_state.py           # 游戏状态管理（PvE/PvP）
├── config.json             # 配置文件（架构/性能/规则）
├── requirements.txt        # Python 依赖
├── .gitignore
├── static/
│   ├── index.html          # 主页面（Fluent UI）
│   ├── css/style.css       # 深色主题样式
│   └── js/main.js          # 前端逻辑
└── engine/                 # RapFi 引擎与模型
    ├── config.toml         # 引擎配置（最强参数）
    ├── pbrain-rapfi-windows-*.exe       # Windows 引擎
    ├── pbrain-rapfi-linux-clang-*       # Linux 引擎
    ├── pbrain-rapfi-macos-apple-silicon # macOS 引擎
    ├── mix9svqfreestyle_bsmix.bin.lz4   # 自由规则模型
    ├── mix9svqstandard_bs15.bin.lz4     # 标准规则模型
    ├── mix9svqrenju_bs15_black.bin.lz4  # 连珠规则-黑棋模型
    ├── mix9svqrenju_bs15_white.bin.lz4  # 连珠规则-白棋模型
    └── model210901.bin                  # 默认模型
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
         ├─ 每层 aspirationSearch() 渴望窗口搜索
         │    └─ search() AlphaBeta 递归
         │         ├─ 置换表 probe() 查询
         │         ├─ Null Move 剪枝
         │         ├─ Killer Move 优先
         │         ├─ History Heuristic 排序
         │         ├─ VCF/VCT 着法生成
         │         └─ 评估器 evaluate()
         └─ 时间到 → 返回最佳着法
```

### VCF/VCT 搜索

- **VCF**：通过连续冲四寻找必胜路线（`vcfsearch`/`vcfdefend`）
- **VCT**：通过连续活三威胁寻找必胜路线
- 在搜索深度 ≤ 0 时自动触发

## 🌐 HTTP API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/state` | 获取游戏状态 |
| GET | `/api/config` | 获取引擎配置 |
| GET | `/api/rules` | 获取规则列表 |
| GET | `/api/engines` | 列出可用引擎 |
| POST | `/api/new_game` | 开始新对局 |
| POST | `/api/move` | 玩家下子 |
| POST | `/api/ai_move` | AI 下子 |
| POST | `/api/undo` | 后退 |
| POST | `/api/redo` | 前进 |
| POST | `/api/jump` | 跳转 |
| POST | `/api/config` | 更新配置 |
| POST | `/api/architecture` | 切换架构 |

## 📦 配置文件

### `config.json`（应用配置）

```json
{
    "engine": {
        "architecture": "auto",
        "max_memory_mb": 512,
        "thread_num": 0,
        "timeout_turn_ms": 8000
    },
    "game": {
        "mode": "pve"
    }
}
```

### `engine/config.toml`（引擎配置）

- 置换表 256MB
- 最大搜索深度 200
- 数据库启用
- Aspiration Window 启用
- 多线程自动

## 🙏 致谢

- **引擎**：[RapFi](https://github.com/dhbloo/rapfi) by dhbloo
- **模型**：mix9svq 系列
- **设计**：Microsoft Fluent UI / Windows 11

## 📄 License

GPL-3.0（继承自 RapFi 引擎）
