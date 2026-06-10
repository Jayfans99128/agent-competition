# ---------- 公共文本清洗工具 ----------
import re

# 最大返回长度（字符），避免 context 过长撑爆 token
MAX_CONTEXT_LENGTH = 3000


def clean_text(text: str) -> str:
    """
    数据清洗阶段：加载原始文本后，压缩多余空白和换行。
    - 连续 3 个以上换行 → 2 个换行（保留段落间距）
    - 连续空格/tab → 单个空格
    - 去掉行首行尾空白
    - 去掉首尾空行
    """
    if not text:
        return text

    # 1. 连续空格/tab → 单个空格
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # 2. 连续 3 个以上换行 → 2 个换行（保留一个空行作为段落分隔）
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 3. 去掉每行首尾空白
    text = '\n'.join(line.strip() for line in text.split('\n'))

    # 4. 去掉首尾空行
    text = text.strip('\n')

    return text


def filter_context_for_llm(text: str, max_length: int = MAX_CONTEXT_LENGTH) -> str:
    """
    大模型输入前：过滤和清洗检索到的 Context。
    - 移除纯空字段（如"：无"、"：无单独划线"等）
    - 对超长字段值做截断
    - 压缩多余空白
    - 控制总长度，避免超出 token 限制
    """
    if not text:
        return text

    # 1. 移除无意义的值
    #    - 字段值为"无"或"无单独划线…"（剔除空值行，但不消费换行符）
    text = re.sub(r'[^：；\n]+：无(?:单独划线[^；\n]*)?[；]?', '', text)
    #    - 字段值为纯括号注释（如"备注：（详见官网）"），兼容全角/半角括号
    text = re.sub(r'[^：；\n]+：[（(][^）)\n]*[）)][；]?', '', text)
    #    - 清理残留/多余的分号（字段被剔除后留下的）
    text = re.sub(r'[；;][ \t]*(?=【)', '', text)   # 标题前的分号（不吞换行）
    text = re.sub(r'[；;][ \t]*[；;]', '；', text)  # 连续分号
    text = re.sub(r'^[；;][ \t]*', '', text, flags=re.MULTILINE)
    text = re.sub(r'[ \t]*[；;][ \t]*$', '', text, flags=re.MULTILINE)

    # 2. 长值截断：每行超过 200 字符的部分截掉
    lines = text.split('\n')
    filtered = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 跳过纯分隔线和注释分隔线（如 "# ===="、"---"、"___"）
        if re.fullmatch(r'[#\s]*[-=_#]{3,}[=\s#-]*', line):
            continue
        # 跳过纯提示性行（"建议"、"提示"开头的行已经在 query 函数里加了，这里不过滤）
        if len(line) > 200:
            # 找第一个句号/分号处截断
            cut = max(line.rfind('。', 0, 200), line.rfind('；', 0, 200), 190)
            line = line[:cut] + '…'
        filtered.append(line)

    text = '\n'.join(filtered)

    # 3. 再次压缩空白
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 4. 控制总长度
    if len(text) > max_length:
        # 在 max_length 处截断，尽量在换行处断开
        cut = text.rfind('\n', 0, max_length)
        if cut < max_length // 2:
            cut = max_length
        text = text[:cut] + '\n…(结果过长，已截断)'

    return text.strip()


from .manager import query_knowledge_base
from .exam_manager import query_kaoyan_scores, query_guokao_scores
from .school_manager import query_kaoyan_school
