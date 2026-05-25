import os

def list_files(path: str = ".") -> str:
    try:
        items = os.listdir(path)
        return "\n".join(items)
    except Exception as e:
        return f"列出文件失败: {e}"

def read_file(filepath: str) -> str:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"读取文件失败: {e}"
