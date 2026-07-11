# GomokuAI

> 基于 [Rapfi](https://github.com/dhbloo/rapfi) 引擎的五子棋 Web 应用,编译为 WebAssembly,Fluent 风格现代 UI + 深色模式。

## 项目简介

GomokuAI 将最新版 Rapfi 五子棋引擎(alpha-beta 搜索 + NNUE 评估)编译为 WebAssembly,集成到现代化前端,构建出可直接部署的五子棋分析 Web 应用。

- **引擎**:Rapfi 0.43.02(commit `3aedf3a`),7 个 WASM 变体覆盖所有浏览器
- **权重**:mix9svq NNUE + classical 经典评估
- **前端**:Vue 2 + Vuex + Vux UI,Fluent Design 风格
- **特性**:深色/浅色/跟随系统主题、毛玻璃效果、平滑动画、PWA 离线

## 快速开始

### 方式一:Python 服务器(推荐,支持多线程)

```bash
# 解压后进入 dist 目录
cd dist

# 运行附带的 Python 服务器(自动设置 COOP/COEP 头)
python serve.py

# 浏览器打开 http://localhost:8000
```

> **为什么需要 `serve.py`?**
> 多线程 WASM 引擎依赖 `SharedArrayBuffer`,浏览器要求服务器设置 `Cross-Origin-Embedder-Policy: require-corp` 和 `Cross-Origin-Opener-Policy: same-origin` 头才会启用。`python -m http.server` 不设置这些头,所以多线程引擎无法加载。`serve.py` 自动处理这个问题。

### 方式二:任意静态服务器(仅单线程)

```bash
cd dist
npx http-server -p 8000
# 或
python -m http.server 8000
```

> 注意:这种方式下多线程引擎不可用,会自动降级为单线程(较慢)。

### 方式三:Nginx(生产部署)

```nginx
server {
    listen 80;
    root /path/to/dist;

    # 关键:为所有响应设置 COOP/COEP 头(启用多线程)
    add_header Cross-Origin-Embedder-Policy "require-corp" always;
    add_header Cross-Origin-Opener-Policy "same-origin" always;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # WASM 文件设置正确 MIME
    location ~* \.wasm$ {
        types { application/wasm wasm; }
    }
}
```

## 功能特性

### UI / 主题
- **Fluent Design 风格**:圆角卡片、毛玻璃半透明、柔和阴影
- **深色模式**:设置 → 外观 → 主题,支持 浅色/深色/跟随系统
- **平滑过渡**:所有元素主题切换时平滑动画,无闪烁
- **现代化组件**:Fluent 风格按钮、开关、输入框、分段选择器

### 引擎
- **7 个 WASM 变体**:自动根据浏览器能力选择最优版本
  - `rapfi-multi-simd128-relaxed` — 最快(多线程 + Relaxed SIMD)
  - `rapfi-multi-simd128` — 多线程 + SIMD128
  - `rapfi-multi` — 多线程
  - `rapfi-single-simd128` — 单线程 + SIMD
  - `rapfi-single` — 单线程(兼容性最好)
  - `fallback/*` — 不带 NNUE 权重的轻量版(不支持 Service Worker 时用)
- **NNUE 权重**:mix9svq(40MB,首次加载后缓存)

### 关于页面
- 精简为纯 FAQ,移除版本号、更新记录、关于应用等冗余内容

## 目录结构

```
GomokuAI/
├── dist/                       # 构建产物(可直接部署)
│   ├── index.html
│   ├── serve.py                # 带 COOP/COEP 头的 Python 服务器
│   ├── build/                  # 7 个 WASM 引擎变体 + NNUE 权重
│   ├── js/, css/, fonts/
│   ├── service-worker.js       # PWA 离线缓存
│   └── manifest.json
├── public/                     # 前端 public 目录(含编译好的引擎)
│   └── build/
├── src/
│   ├── ai/                     # 引擎 worker 与封装
│   ├── components/             # 棋盘、最佳走法组件
│   ├── views/                  # 主页、对局、设置、关于
│   ├── store/                  # Vuex 状态管理
│   ├── styles/modern.less      # Fluent 风格主题系统
│   ├── theme.js                # 深色/浅色模式管理
│   └── locales/                # 7 种语言
├── serve.py                    # 服务器脚本(源码版)
├── package.json
└── vue.config.js
```

## 本地开发

```bash
npm install --legacy-peer-deps

# 开发模式(热更新)
NODE_OPTIONS=--openssl-legacy-provider npm run serve

# 生产构建
NODE_OPTIONS=--openssl-legacy-provider npm run build
```

> Node.js 17+ 需要 `NODE_OPTIONS=--openssl-legacy-provider`。

## 致谢

- **Rapfi 引擎**:[dhbloo/rapfi](https://github.com/dhbloo/rapfi),GPL v3
- **gomoku-calculator 前端**:[dhbloo/gomoku-calculator](https://github.com/dhbloo/gomoku-calculator)
- **NNUE 权重**:[dhbloo/rapfi-networks](https://github.com/dhbloo/rapfi-networks)

## License

GPL v3 — 继承自 Rapfi 引擎。
