import sys
import os

# 确保项目路径在sys.path中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.ocr_tools import ocr_image_from_url
    print("ocr_image_from_url 导入成功!")

    # 查看函数是否定义
    import inspect
    print("函数签名:")
    print(inspect.signature(ocr_image_from_url))

except ImportError as e:
    print(f"导入错误: {e}")
    print("尝试检查依赖...")

    try:
        import pytesseract
        print("pytesseract 导入成功!")
        print(f"pytesseract 版本: {pytesseract.__version__}")
    except ImportError as e2:
        print(f"pytesseract 导入失败: {e2}")

    # 检查环境变量和工作目录
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python可执行文件: {sys.executable}")
    print(f"Python路径: {sys.path[:3]}")