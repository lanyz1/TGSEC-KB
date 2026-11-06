"""
NVD CLI 入口脚本

直接运行此文件即可使用命令行工具：
    python main.py cve get CVE-2021-44228
    python main.py cve search -k log4j
    python main.py config set api_key your-key
"""

import sys
from pathlib import Path

# 将 src 目录加入模块搜索路径，使相对导入正常工作
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import app

if __name__ == "__main__":
    app()
