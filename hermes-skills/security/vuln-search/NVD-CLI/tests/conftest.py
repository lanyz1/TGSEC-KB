"""
测试配置 - 将 src 目录加入模块搜索路径
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
