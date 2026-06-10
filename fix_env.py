#!/usr/bin/env python3
"""
项目依赖修复和启动脚本
"""

import os
import sys
import subprocess

def install_requirements():
    """安装所有必要依赖"""
    try:
        # 安装基础依赖
        packages = [
            'pytesseract',
            'Pillow',
            'packaging',
            'openai',
            'python-dotenv'
        ]

        for package in packages:
            print(f"Installing {package}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package, "--quiet"
            ])
            print(f"Done: {package}")

        return True
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        return False

def test_imports():
    """测试关键导入是否成功"""
    required_imports = [
        'pytesseract',
        'Pillow',
        'backend.ocr_tools'
    ]

    for imp in required_imports:
        try:
            if imp.startswith('backend.'):
                # 特殊处理backend模块
                print(f"Testing import: {imp}")
                __import__(imp)
            else:
                print(f"Testing import: {imp}")
                __import__(imp)
            print(f"Success: {imp}")
        except ImportError as e:
            print(f"Failed: {imp} - {e}")
            return False

    return True

def fix_path():
    """修复Python路径"""
    project_root = os.path.dirname(os.path.abspath(__file__))

    # 确保项目根目录在Python路径中
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"Added project root to path: {project_root}")

    # 添加backend目录到路径
    backend_path = os.path.join(project_root, 'backend')
    if backend_path not in sys.path:
        sys.path.insert(1, backend_path)
        print(f"Added backend to path: {backend_path}")

    return True

def main():
    print("=== Project Fix Tool ===")

    # 1. 修复路径
    print("\n1. Fixing Python path...")
    fix_path()

    # 2. 安装依赖
    print("\n2. Installing dependencies...")
    if not install_requirements():
        print("Failed to install dependencies")
        return False

    # 3. 测试导入
    print("\n3. Testing imports...")
    if not test_imports():
        print("Import test failed")
        return False

    print("\nAll dependencies fixed successfully!")
    print("You can now run the backend application.")
    return True

if __name__ == "__main__":
    main()