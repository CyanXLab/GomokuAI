#!/usr/bin/env python3
"""
GomokuAI 静态文件服务器.

为什么需要这个脚本?
-------------------
GomokuAI 的多线程 WASM 引擎依赖 SharedArrayBuffer,而浏览器要求
服务器对所有响应设置以下两个 HTTP 头才会启用 SharedArrayBuffer:

    Cross-Origin-Embedder-Policy: require-corp
    Cross-Origin-Opener-Policy: same-origin

python -m http.server 不设置这些头,所以多线程引擎无法加载。
本脚本自动设置这些头,让多线程引擎在 localhost 上正常工作。

用法:
    python serve.py              # 默认 8000 端口
    python serve.py 9000         # 指定端口
    python serve.py --dir dist   # 指定目录(默认 dist)

然后浏览器打开 http://localhost:8000
"""

import sys
import os
import argparse
import functools
from http.server import HTTPServer, SimpleHTTPRequestHandler


class GomokuAIHandler(SimpleHTTPRequestHandler):
    """自定义 handler,为所有响应添加 COOP/COEP 头和正确的 MIME 类型。"""

    def end_headers(self):
        # 启用 SharedArrayBuffer 所需的跨域隔离头
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Resource-Policy', 'same-site')
        super().end_headers()

    def guess_type(self, path):
        """为 .wasm 文件设置正确的 MIME 类型。"""
        mimetype = super().guess_type(path)
        if path.endswith('.wasm'):
            return 'application/wasm'
        return mimetype

    def log_message(self, format, *args):
        # 简化日志,加上颜色
        msg = format % args
        if '200' in msg or '304' in msg:
            # 绿色
            print(f'\033[92m{self.address_string()}\033[0m - {msg}')
        elif '404' in msg or '400' in msg or '500' in msg:
            # 红色
            print(f'\033[91m{self.address_string()}\033[0m - {msg}')
        else:
            print(f'{self.address_string()} - {msg}')


def main():
    parser = argparse.ArgumentParser(
        description='GomokuAI 静态文件服务器(带 COOP/COEP 头)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
启动后浏览器打开 http://localhost:8000 即可使用。
按 Ctrl+C 停止。
        '''
    )
    parser.add_argument('port', nargs='?', type=int, default=8000,
                        help='端口号(默认 8000)')
    parser.add_argument('--dir', default='dist',
                        help='要服务的目录(默认 dist)')
    parser.add_argument('--host', default='0.0.0.0',
                        help='监听地址(默认 0.0.0.0,即所有接口)')
    args = parser.parse_args()

    # 切换到目标目录
    if not os.path.isdir(args.dir):
        print(f'\033[91m错误: 目录 "{args.dir}" 不存在\033[0m')
        print(f'当前目录: {os.getcwd()}')
        print('请先运行 npm run build 生成 dist/,或用 --dir 指定其他目录')
        sys.exit(1)

    os.chdir(args.dir)

    handler = functools.partial(GomokuAIHandler, directory=args.dir)

    server = HTTPServer((args.host, args.port), handler)

    print(f'''
\033[96m╔══════════════════════════════════════════════╗
║          GomokuAI Server                       ║
╚══════════════════════════════════════════════╝\033[0m

  目录: \033[93m{os.path.abspath(args.dir)}\033[0m
  地址: \033[92mhttp://localhost:{args.port}\033[0m

  COOP/COEP 头: \033[92m已启用\033[0m (多线程引擎可用)
  WASM MIME:    \033[92m已配置\033[0m

  按 \033[93mCtrl+C\033[0m 停止服务器
''')

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n\033[93m服务器已停止\033[0m')
        server.server_close()


if __name__ == '__main__':
    main()
