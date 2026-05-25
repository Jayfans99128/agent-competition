import json

from backend.config import client, MODEL


def analyze(filepath: str) -> dict:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        prompt = f"""
请你从下面简历中提取结构化信息。

1. 返回合法 JSON
2. 不允许输出 markdown
3. 不允许输出解释
4. 缺失字段使用空字符串或空数组填充
返回格式：

{{
  "name": "",
  "education": [],
  "skills": [],
  "projects": [],
  "work_experience": []
}}


简历内容：
{content}
"""
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": prompt
                }
            ]
        )
        test = response.choices[0].message.content

        # 尝试提取 JSON：先试直接解析，再试从 markdown 代码块提取
        def extract_json(text):
            text = text.strip()
            # 直接解析
            try:
                return json.loads(text)
            except Exception:
                pass
            # 从 ```json ... ``` 中提取
            import re
            m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(1).strip())
                except Exception:
                    pass
            # 从第一个 { 到最后一个 }
            start = text.find('{')
            end = text.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end+1])
                except Exception:
                    pass
            return None

        data = extract_json(test)
        if data is not None:
            return data
        return {
            "error": "无法从模型回复中提取有效 JSON",
            "raw_response": test,
        }

    except Exception as e:
        return {
            "error": str(e)
        }
