#!/usr/bin/env python3
"""
项目依赖修复和启动脚本
"""

import os
import sys
import subprocess

def ensure_virtual_environment():
    """确保虚拟环境已激活"""
    # 检查是否在虚拟环境中
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✓ 已在虚拟环境中")
        return True
    else:
        print("✗ 未在虚拟环境中，请激活虚拟环境")
        # 检查虚拟环境是否可用
        venv_path = os.path.join(os.getcwd(), '.venv')
        if os.path.exists(venv_path):
            print(f"✓ 找到虚拟环境: {venv_path}")
            return True
        else:
            print("✗ 未找到虚拟环境")
            return False

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
            print(f"安装 {package}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package, "--quiet"
            ])
            print(f"✓ {package} 安装完成")

        return True
    except Exception as e:
        print(f"✗ 安装依赖失败: {e}")
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
                module_path = imp.replace('backend.', 'backend/')
                print(f"测试导入: {imp}")
                __import__(imp)
            else:
                print(f"测试导入: {imp}")
                __import__(imp)
            print(f"✓ {imp} 导入成功")
        except ImportError as e:
            print(f"✗ {imp} 导入失败: {e}")
            return False

    return True

def fix_path_problem():
    """修复Python路径问题"""
    project_root = os.path.dirname(os.path.abspath(__file__))

    # 确保项目根目录在Python路径中
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"添加项目根目录到路径: {project_root}")

    # 添加backend目录到路径
    backend_path = os.path.join(project_root, 'backend')
    if backend_path not in sys.path:
        sys.path.insert(1, backend_path)
        print(f"添加backend目录到路径: {backend_path}")

    return True

def main():
    print("=== 项目依赖修复工具 ===")

    # 1. 修复路径问题
    print("\n1. 正在修复Python路径...")
    fix_path_problem()

    # 2. 检查虚拟环境
    print("\n2. 检查虚拟环境...")
    if not ensure_virtual_environment():
        print("请先激活虚拟环境后再运行")
        return False

    # 3. 安装依赖
    print("\n3. 安装依赖包...")
    if not install_requirements():
        print("依赖安装失败，无法继续")
        return False

    # 4. 测试导入
    print("\n4. 测试关键导入...")
    if not test_imports():
        print("导入测试失败")
        return False

    print("\n✓ 所有依赖已成功修复和安装")
    print("现在可以正常运行后端应用了！")
    return True

if __name__ == "__main__":
    main()