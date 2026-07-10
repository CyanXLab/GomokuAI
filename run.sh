#!/bin/bash
cd "$(dirname "$0")"
PYTHON=${PYTHON:-python3}
if ! command -v $PYTHON &> /dev/null; then
    echo "[错误] 未找到 Python3"
    exit 1
fi
if ! $PYTHON -c "import flask" &> /dev/null; then
    echo "[安装] 正在安装依赖..."
    $PYTHON -m pip install flask || exit 1
fi
$PYTHON run.py "$@"
