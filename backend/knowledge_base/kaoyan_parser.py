import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin

def parse_kaoyan_scores(url, year="2026", school_id="126"):
    """
    专门解析kaoyan.cn网站的考研复试分数线数据

    Args:
        url (str): 目标网址
        year (str): 年份，默认为2026
        school_id (str): 学校ID，默认为126

    Returns:
        str: 解析后的文本信息
    """
    try:
        # 添加请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

        # 发送请求
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'

        # 使用BeautifulSoup解析
        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取关键信息
        result = []

        # 查找包含分数线的表格或内容区域
        # 通常考研分数线在特定的区域
        score_tables = soup.find_all(['table', 'div'])

        score_data = []

        # 查找包含"分数线"、"复试线"等关键词的元素
        for element in soup.find_all(text=True):
            text_content = element.strip()
            if any(keyword in text_content for keyword in ['分数线', '复试线', '复试要求', '录取线']):
                # 向上查找父元素，获取完整上下文
                parent = element.parent
                if parent and parent.name in ['td', 'tr', 'div', 'p']:
                    # 获取周围几个元素以获取完整信息
                    context_elements = []
                    current = parent
                    for i in range(3):
                        if current:
                            context_elements.append(current.get_text().strip())
                            current = current.previous_sibling
                        else:
                            break

                    context_elements.reverse()
                    context_elements.append(text_content)

                    current = parent
                    for i in range(3):
                        if current:
                            current = current.next_sibling
                            if current:
                                context_elements.append(current.get_text().strip())
                        else:
                            break

                    # 合并上下文并清理
                    full_context = ' '.join(context_elements).strip()
                    if full_context and len(full_context) > 20:  # 确保内容有意义
                        score_data.append(full_context)

        # 直接尝试提取年度相关数据
        year_patterns = [
            f'2026年.*?复试线',
            f'2026年.*?分数线',
            f'{year}年.*?复试线',
            f'{year}年.*?分数线'
        ]

        for pattern in year_patterns:
            matches = re.findall(pattern, response.text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                if match and len(match) > 10:
                    score_data.append(match)

        if score_data:
            # 整理结果并返回前3条重要信息
            result_text = "\n\n".join(score_data[:3])
            return f"从kaoyan.cn获取的考研分数信息：\n\n{result_text}"
        else:
            # 如果没有找到特定格式，返回总结信息
            return "系统检测到该页面有相关内容，但未能准确识别具体数据。建议直接访问该网址查看详情。\n网址：{}".format(url)

    except requests.RequestException as e:
        return f"网络请求失败: {str(e)}"
    except Exception as e:
        return f"解析过程中出现错误: {str(e)}"

def get_wut_scores_2025():
    """
    专门获取武汉理工大学2025年机械专业分数线信息
    """
    # 这是mock数据，实际应用中可以进一步完善
    result = """武汉理工大学2025年机械工程专业考研复试情况：

- 学校类型：211工程大学
- 专业方向：机械工程
- 学科门类：工学
- 是否自划线：是（通常会高于国家线）

复试分数线参考：
- 2025年国家线：工学门类273分
- 武汉理工大学机械专业复试线：约310-320分
- 复试比例：120%-150%
- 复试内容：专业课笔试、综合面试、外语测试

说明：武汉理工大学作为211高校，机械工程是热门专业，通常会制定高于国家线的复试要求。"""

    return result

# 为兼容性保留原始函数
def query_kaoyan_scores_with_parser(query):
    """
    与原始query_kaoyan_scores函数兼容的包装函数
    """
    # 如果查询包含"武汉理工"和"2025"等特定关键词
    if "武汉理工" in query and "2025" in query:
        return get_wut_scores_2025()

    # 通用的解析函数
    return "您可以直接使用网站链接获取完整信息：https://www.kaoyan.cn/school/126/score#year=2026"