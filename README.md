# GomokuPrime

> 基于 [Rapfi](https://github.com/dhbloo/rapfi) 引擎与 [gomoku-calculator](https://github.com/dhbloo/gomoku-calculator) 前端的五子棋 Web 应用,已编译为 WebAssembly 并构建为可部署的静态站点。

## 项目简介

本仓库将最新版 Rapfi 五子棋引擎(基于 alpha-beta 搜索 + NNUE 评估)编译为 WebAssembly,集成到 gomoku-calculator 前端,构建出可直接部署的五子棋分析 Web 应用。

- 引擎版本:Rapfi master 分支(commit `3aedf3a`,版本 0.43.02)
- 神经网络权重:mix9svq(NNUE) + classical(经典评估)
- 前端框架:Vue 2 + Vuex + Vue Router + Vux UI
- 引擎编译:Emscripten 6.0.2,7 个 WASM 变体覆盖所有浏览器能力

## 目录结构

```
GomokuPrime/
├── dist/                       # 构建产物(可直接部署的静态站点)
│   ├── index.html
│   ├── js/, css/, fonts/
│   ├── build/                  # 编译好的 WASM 引擎(5 个完整版本 + fallback)
│   │   ├── rapfi-single.js/.wasm
│   │   ├── rapfi-single-simd128.js/.wasm
│   │   ├── rapfi-multi.js/.wasm
│   │   ├── rapfi-multi-simd128.js/.wasm
│   │   ├── rapfi-multi-simd128-relaxed.js/.wasm
│   │   ├── rapfi.data          # NNUE 权重文件(40MB,所有完整版本共享)
│   │   └── fallback/           # 不带 NNUE 的轻量 fallback 版本
│   ├── service-worker.js       # PWA 离线缓存
│   └── manifest.json
├── public/                     # 前端源码的 public 目录(含编译好的引擎)
│   └── build/                  # 同 dist/build/
├── src/                        # Vue 前端源代码
│   ├── ai/                     # 引擎 worker 与封装
│   ├── components/             # 棋盘、最佳走法等组件
│   ├── views/                  # 主页、对局、设置、关于等页面
│   ├── store/                  # Vuex 状态管理
│   ├── locales/                # 多语言(中文/英文/日文/韩文/俄文/越南文/繁中)
│   └── ...
├── package.json                # npm 依赖与脚本
├── vue.config.js               # Vue CLI 配置(PWA、worker-loader、COOP/COEP)
├── AUTHORS                     # Rapfi 作者名单
└── LICENSE-GPLv3               # Rapfi 引擎遵循 GPL v3
```

## 快速部署

`dist/` 目录是已经构建好的静态站点,可以直接部署到任意静态文件服务器:

```bash
# 方式一:简单 HTTP 服务器
cd dist && npx http-server -p 8080

# 方式二:Nginx
# 将 dist/ 目录配置为 nginx 的 root
```

### 关键部署要求(多线程支持)

浏览器启用 `SharedArrayBuffer`(多线程 WASM 需要)时,要求服务器为**所有响应**(包括 `index.html` 和 `dist/build/` 下的所有 JS/WASM 文件)设置以下 HTTP 头:

```
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Opener-Policy: same-origin
```

同时建议为 `.wasm` 文件设置正确的 MIME 类型:

```
application/wasm  *.wasm
```

Nginx 配置示例:

```nginx
server {
    listen 80;
    root /path/to/dist;

    location / {
        add_header Cross-Origin-Embedder-Policy "require-corp" always;
        add_header Cross-Origin-Opener-Policy "same-origin" always;
        try_files $uri $uri/ /index.html;
    }

    location ~* \.wasm$ {
        add_header Cross-Origin-Embedder-Policy "require-corp" always;
        add_header Cross-Origin-Opener-Policy "same-origin" always;
        types { application/wasm wasm; }
    }
}
```

## 本地开发

```bash
# 安装依赖
npm install --legacy-peer-deps

# 开发模式(热更新)
NODE_OPTIONS=--openssl-legacy-provider npm run serve

# 生产构建
NODE_OPTIONS=--openssl-legacy-provider npm run build
```

> Node.js 17+ 需要设置 `NODE_OPTIONS=--openssl-legacy-provider`,因为旧版 webpack 依赖的 OpenSSL API 已被废弃。

## 引擎构建说明

`public/build/` 下的 7 个 WASM 引擎变体由 Rapfi 源码编译,编译参数如下:

| 文件名                        | 多线程 | SIMD128 | Relaxed SIMD | NNUE 权重 |
|-------------------------------|--------|---------|--------------|-----------|
| rapfi-single                  | 否     | 否      | 否           | 是        |
| rapfi-single-simd128          | 否     | 是      | 否           | 是        |
| rapfi-multi                   | 是     | 否      | 否           | 是        |
| rapfi-multi-simd128           | 是     | 是      | 否           | 是        |
| rapfi-multi-simd128-relaxed   | 是     | 是      | 是           | 是        |
| fallback/rapfi-single         | 否     | 否      | 否           | 否(仅配置)|
| fallback/rapfi-multi          | 是     | 否      | 否           | 否(仅配置)|

前端通过 `wasm-feature-detect` 库在运行时探测浏览器能力,自动选择最优引擎加载。当浏览器不支持 Service Worker 时,使用 fallback 版本(只加载 18KB 配置文件,而非 40MB NNUE 权重)以减少流量。

### 从源码重新编译引擎

```bash
# 安装 Emscripten SDK
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk && ./emsdk install latest && ./emsdk activate latest
source ./emsdk_env.sh

# 克隆 Rapfi 源码与权重
git clone https://github.com/dhbloo/rapfi.git
cd rapfi
git clone https://github.com/dhbloo/rapfi-networks.git Networks

# 编译各变体(以 rapfi-multi-simd128 为例)
cd Rapfi
mkdir -p build/wasm-multi-simd128 && cd build/wasm-multi-simd128
emcmake cmake ../.. -DCMAKE_BUILD_TYPE=Release -DNO_COMMAND_MODULES=ON \
    -DUSE_WASM_SIMD=ON -DUSE_WASM_SIMD_RELAXED=OFF
emmake cmake --build .

# 产物 rapfi-multi-simd128.js/.wasm/.data 复制到 gomoku-calculator/public/build/
```

## 致谢

- **Rapfi 引擎**:由 [dhbloo](https://github.com/dhbloo) 开发,GPL v3 协议
- **gomoku-calculator 前端**:由 [dhbloo](https://github.com/dhbloo) 开发
- **NNUE 权重**:来自 [rapfi-networks](https://github.com/dhbloo/rapfi-networks) 仓库

本仓库是以上项目的集成构建产物,遵循相同的 GPL v3 协议。
