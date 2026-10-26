"""
本地测试脚本 -- 无需启动 Web 服务，直接测试简历分析模块的 JSON 输出。

用法：
    python test_resume.py                    # 测试 resume_analyzer (analyze)
    python test_resume.py --template          # 测试 template_filler (提取+填充)
    python test_resume.py --both              # 两个都测
    python test_resume.py --file 简历示例1.docx  # 指定简历文件
"""

import sys
import os
import json

# 确保项目根目录在 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document


def docx_to_text(filepath: str) -> str:
    """将 DOCX 简历转为纯文本"""
    doc = Document(filepath)
    return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())


def test_analyze(resume_text: str):
    """测试 resume_analyzer.py 的 analyze 函数"""
    print("=" * 60)
    print("[测试] resume_analyzer.analyze()")
    print("=" * 60)

    # 先把文本写入临时文件（analyze 函数需要文件路径）
    tmp_path = os.path.join(os.path.dirname(__file__), "_test_resume.txt")
    with open(tmp_path, 'w', encoding='utf-8') as f:
        f.write(resume_text)

    from backend.skill.resume_analyzer.resume_analyzer import analyze
    result = analyze(tmp_path)

    os.remove(tmp_path)

    print("\n[简历文本 - 前200字]:")
    print("-" * 40)
    print(resume_text[:200])
    print()

    print("\n[提取结果 JSON]:")
    print("-" * 40)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    return result


def test_template_filler(resume_text: str):
    """测试 template_filler.py 的 _extract_resume_data 函数"""
    print("=" * 60)
    print("[测试] template_filler._extract_resume_data()")
    print("=" * 60)

    from backend.skill.resume_analyzer.template_filler import _extract_resume_data

    result = _extract_resume_data(resume_text)

    print("\n[简历文本 - 前200字]:")
    print("-" * 40)
    print(resume_text[:200])
    print()

    print("\n[提取结果 JSON]:")
    print("-" * 40)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    return result


def main():
    # 解析命令行参数
    mode = "analyze"  # 默认测试 analyze
    resume_file = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--template":
            mode = "template"
        elif args[i] == "--both":
            mode = "both"
        elif args[i] == "--file" and i + 1 < len(args):
            resume_file = args[i + 1]
            i += 1
        else:
            resume_file = args[i]
        i += 1

    # 找简历文件
    if resume_file:
        if not os.path.exists(resume_file):
            print(f"[ERROR] 文件不存在: {resume_file}")
            sys.exit(1)
    else:
        # 自动找第一个示例简历
        for candidate in ["简历示例1.docx"]:
            if os.path.exists(candidate):
                resume_file = candidate
                break
        if not resume_file:
            print("[ERROR] 找不到示例简历文件，请用 --file 指定")
            sys.exit(1)

    print(f"[INFO] 使用简历文件: {resume_file}")
    resume_text = docx_to_text(resume_file)

    if not resume_text:
        print("[ERROR] 简历文件内容为空")
        sys.exit(1)

    if mode in ("analyze", "both"):
        test_analyze(resume_text)
        print()

    if mode in ("template", "both"):
        test_template_filler(resume_text)
        print()

    print("[DONE] 测试完成")


if __name__ == "__main__":
    main()