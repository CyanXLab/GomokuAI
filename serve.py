#!/usr/bin/env python3
"""
GomokuAI 静态文件服务器 (HTTPS + COOP/COEP).

特性:
  - 自动生成自签名 SSL 证书,默认 HTTPS
  - 自动设置 COOP/COEP 头(启用 SharedArrayBuffer,多线程 WASM 可用)
  - 自动设置 .wasm 的 application/wasm MIME
  - 默认服务当前目录

用法:
    python serve.py                # HTTPS, 端口 8443, 当前目录
    python serve.py 9000           # HTTPS, 指定端口
    python serve.py --http         # HTTP 模式, 端口 8000
    python serve.py --dir dist     # 指定目录
    python serve.py --open         # 启动时自动打开浏览器

浏览器打开:
    HTTPS 模式: https://localhost:8443
    HTTP 模式:  http://localhost:8000

注意:
    HTTPS 自签名证书首次访问会显示"不安全"警告,
    点击"高级" -> "继续前往" 即可,这是正常的。
"""

import sys
import os
import ssl
import argparse
import functools
import subprocess
import shutil
from http.server import HTTPServer, SimpleHTTPRequestHandler


# ========== 配置 ==========
DEFAULT_HTTP_PORT = 8000
DEFAULT_HTTPS_PORT = 8443
CERT_DIR = os.path.join(os.path.expanduser('~'), '.gomokuai')
CERT_FILE = os.path.join(CERT_DIR, 'cert.pem')
KEY_FILE = os.path.join(CERT_DIR, 'key.pem')


# ========== Handler ==========
class GomokuAIHandler(SimpleHTTPRequestHandler):
    """自定义 handler:COOP/COEP 头 + WASM MIME + 彩色日志。"""

    def end_headers(self):
        # 启用 SharedArrayBuffer 所需的跨域隔离头
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Resource-Policy', 'same-site')
        super().end_headers()

    def guess_type(self, path):
        mimetype = super().guess_type(path)
        if path.endswith('.wasm'):
            return 'application/wasm'
        return mimetype

    def log_message(self, format, *args):
        msg = format % args
        # 颜色码在 Windows 下也要工作 (Python 3.6+ ANSI 支持)
        if ' 200 ' in msg or ' 304 ' in msg:
            print(f'\033[92m{self.address_string()}\033[0m - {msg}')
        elif ' 404 ' in msg or ' 400 ' in msg or ' 500 ' in msg:
            print(f'\033[91m{self.address_string()}\033[0m - {msg}')
        else:
            print(f'{self.address_string()} - {msg}')


# ========== SSL 证书 ==========
def ensure_certificate():
    """确保自签名 SSL 证书存在,不存在则生成。返回 (cert_file, key_file)。"""
    # 如果两个文件都存在,直接复用
    if os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE):
        return CERT_FILE, KEY_FILE

    os.makedirs(CERT_DIR, exist_ok=True)

    print('\033[93m正在生成自签名 SSL 证书...\033[0m')

    # 优先用 openssl (跨平台,如果安装了)
    if shutil.which('openssl'):
        try:
            # 生成私钥 + 自签名证书 (有效期 10 年)
            # SAN 包含 localhost 和 127.0.0.1,现代浏览器需要
            cmd = [
                'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
                '-keyout', KEY_FILE,
                '-out', CERT_FILE,
                '-days', '3650',
                '-nodes',
                '-subj', '/CN=localhost',
                '-addext', 'subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1,IP:0.0.0.0',
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            print(f'\033[92m证书已生成(使用 openssl)\033[0m')
            return CERT_FILE, KEY_FILE
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f'\033[93mopenssl 生成失败,改用 Python 内置方法: {e}\033[0m')

    # 用 Python 的 ssl 模块生成 (无需外部依赖)
    _generate_cert_python()
    print(f'\033[92m证书已生成(使用 Python ssl 模块)\033[0m')
    return CERT_FILE, KEY_FILE


def _generate_cert_python():
    """使用 Python 标准库生成自签名证书(无需 openssl)。"""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, u'localhost'),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(u'localhost'),
                    x509.DNSName(u'*.localhost'),
                    x509.IPAddress(__import__('ipaddress').ip_address(u'127.0.0.1')),
                    x509.IPAddress(__import__('ipaddress').ip_address(u'0.0.0.0')),
                ]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        with open(KEY_FILE, 'wb') as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            ))

        with open(CERT_FILE, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        return
    except ImportError:
        pass

    # 最后的兜底:用 ssl 模块的简易方法(证书质量较低,但能用)
    # 这种方式生成的证书不含 SAN,现代浏览器可能会拒绝,但至少能建立连接
    print('\033[93m警告: 无法生成含 SAN 的证书,使用简易证书\033[0m')
    print('\033[93m建议: 安装 openssl 或 pip install cryptography 以获得更好兼容性\033[0m')

    # 用 subprocess 调用 python 自带的 ssl 测试
    # 实际上 Python 标准库没有直接生成证书的 API,这里只能报错
    print('\033[91m错误: 无法生成 SSL 证书\033[0m')
    print('请安装以下任一工具:')
    print('  1. openssl (大多数系统自带)')
    print('  2. pip install cryptography')
    print('或者使用 HTTP 模式: python serve.py --http')
    sys.exit(1)


# ========== 主程序 ==========
def main():
    parser = argparse.ArgumentParser(
        description='GomokuAI 静态文件服务器 (HTTPS + COOP/COEP)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
浏览器打开:
  HTTPS 模式: https://localhost:8443
  HTTP 模式:  http://localhost:8000

首次访问 HTTPS 会显示证书警告,点击"高级"->"继续前往"即可。
        '''
    )
    parser.add_argument('port', nargs='?', type=int, default=None,
                        help='端口号(HTTPS 默认 8443, HTTP 默认 8000)')
    parser.add_argument('--http', action='store_true',
                        help='使用 HTTP 模式(不加密,仅 localhost 可用多线程)')
    parser.add_argument('--dir', default='./',
                        help='要服务的目录(默认当前目录 ./)')
    parser.add_argument('--host', default='0.0.0.0',
                        help='监听地址(默认 0.0.0.0)')
    parser.add_argument('--open', action='store_true',
                        help='启动时自动打开浏览器')
    args = parser.parse_args()

    use_https = not args.http
    if args.port is None:
        port = DEFAULT_HTTPS_PORT if use_https else DEFAULT_HTTP_PORT
    else:
        port = args.port

    # 切换到目标目录
    args.dir = args.dir.rstrip('/\\') or '.'
    if not os.path.isdir(args.dir):
        print(f'\033[91m错误: 目录 "{args.dir}" 不存在\033[0m')
        print(f'当前目录: {os.getcwd()}')
        sys.exit(1)

    abs_dir = os.path.abspath(args.dir)
    os.chdir(args.dir)

    handler = functools.partial(GomokuAIHandler, directory=args.dir)
    server = HTTPServer((args.host, port), handler)

    protocol = 'HTTPS' if use_https else 'HTTP'
    url_scheme = 'https' if use_https else 'http'
    display_host = 'localhost'
    url = f'{url_scheme}://{display_host}:{port}'

    # 配置 SSL
    if use_https:
        try:
            cert_file, key_file = ensure_certificate()
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(certfile=cert_file, keyfile=key_file)
            server.socket = ctx.wrap_socket(server.socket, server_side=True)
        except Exception as e:
            print(f'\033[91mSSL 配置失败: {e}\033[0m')
            print('\033[93m回退到 HTTP 模式\033[0m')
            use_https = False
            protocol = 'HTTP'
            url_scheme = 'http'
            port = DEFAULT_HTTP_PORT
            url = f'{url_scheme}://{display_host}:{port}'
            # 重新创建 HTTP server
            server = HTTPServer((args.host, port), handler)

    print(f'''
\033[96m╔══════════════════════════════════════════════╗
║          GomokuAI Server                       ║
╚══════════════════════════════════════════════╝\033[0m

  协议: \033[93m{protocol}\033[0m
  目录: \033[93m{abs_dir}\033[0m
  地址: \033[92m{url}\033[0m

  COOP/COEP 头: \033[92m已启用\033[0m (多线程引擎可用)
  WASM MIME:    \033[92m已配置\033[0m''')

    if use_https:
        print(f'''
\033[93m  ⚠ 首次访问 HTTPS 会显示"不安全"警告
    点击"高级" -> "继续前往 localhost(不安全)" 即可
    这是自签名证书的正常现象,不影响使用\033[0m''')

    print(f'''
  按 \033[93mCtrl+C\033[0m 停止服务器
''')

    # 自动打开浏览器
    if args.open:
        try:
            if sys.platform == 'win32':
                os.startfile(url)
            elif sys.platform == 'darwin':
                subprocess.run(['open', url])
            else:
                subprocess.run(['xdg-open', url])
        except Exception:
            pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n\033[93m服务器已停止\033[0m')
        server.server_close()


if __name__ == '__main__':
    main()
