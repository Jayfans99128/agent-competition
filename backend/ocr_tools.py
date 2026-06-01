import pytesseract
from PIL import Image
import requests
from io import BytesIO
import os

def ocr_image_from_url(image_url):
    """
    从图片URL提取文本信息
    """
    try:
        # 下载图片
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content))

        # 使用tesseract OCR（支持中英文）
        text = pytesseract.image_to_string(image, lang='chi_sim+eng')
        return text.strip()

    except Exception as e:
        return f"OCR处理失败: {str(e)}"

def ocr_image_from_file(file_path):
    """
    从本地文件路径提取文本
    """
    try:
        if not os.path.exists(file_path):
            return f"文件不存在: {file_path}"

        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang='chi_sim+eng')
        return text.strip()
    except Exception as e:
        return f"OCR处理失败: {str(e)}"

def ocr_image_from_bytes(image_bytes):
    """
    从字节数据中提取文本
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang='chi_sim+eng')
        return text.strip()
    except Exception as e:
        return f"OCR处理失败: {str(e)}"

def check_ocr_support():
    """
    检查OCR功能是否可用
    """
    try:
        # 尝试简单测试
        test_image = Image.new('RGB', (100, 100), color='white')
        result = pytesseract.image_to_string(test_image, lang='chi_sim+eng')
        return True, "OCR功能正常"
    except Exception as e:
        return False, f"OCR功能不可用: {str(e)}"