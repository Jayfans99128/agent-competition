#!/usr/bin/env python3
"""
修复OCR依赖问题的脚本
"""

import os
import sys
import subprocess
import importlib

def check_and_install_pytesseract():
    """检查并安装pytesseract"""
    try:
        # 首先尝试导入
        import pytesseract
        print("✓ pytesseract 已经安装")
        return True
    except ImportError:
        print("✗ pytesseract 未安装，正在安装...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "pytesseract", "--quiet"
            ])
            print("✓ pytesseract 安装成功")
            return True
        except Exception as e:
            print(f"✗ 安装失败: {e}")
            return False

def fix_import_issue():
    """修复导入问题"""
    # 确保当前目录在Python路径中
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        print("添加当前目录到Python路径")

    # 尝试导入拓展模块
    try:
        import backend.ocr_tools
        print("✓ OCR工具模块导入成功")
        return True
    except ImportError as e:
        print(f"✗ OCR工具模块导入失败: {e}")
        # 尝试使用pip安装缺少的模块
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "Pillow", "--quiet"
            ])
            print("✓ Pillow 安装成功")
            return True
        except Exception as e2:
            print(f"✗ 安装Pillow失败: {e2}")
            return False

def main():
    print("=== 正在修复OCR依赖问题 ===")

    # 检查并安装pytesseract
    if not check_and_install_pytesseract():
        print("无法安装pytesseract，程序可能无法运行")
        return False

    # 检查导入
    if not fix_import_issue():
        print("无法修复导入问题")
        return False

    print("✓ 所有依赖已修复")
    return True

if __name__ == "__main__":
    main()