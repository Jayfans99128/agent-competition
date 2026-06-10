import json
import logging
import re
import time

MAX_TOOL_ROUNDS = 5     # 最大工具调用轮次
MAX_TOKENS = 2048        # 单次生成上限（prompt 要求简短，工具调用也需要 token）
STREAM_CHUNK_SIZE = 12   # 流式输出每块字符数
STREAM_DELAY = 0.025     # 流式输出块间延迟（秒），让前端有渐进感

logger = logging.getLogger("zhipig")


def _clean_output(text: str) -> str:
    """清洗模型输出：压缩多余空行、去掉首尾空白"""
    if not text:
        return text
    # 1. 去掉每行首尾空白
    text = '\n'.join(line.strip() for line in text.split('\n'))
    # 2. 去掉首尾空行
    text = text.strip('\n')
    # 3. 连续 3 个以上换行 → 2 个换行（先 strip 再压缩，避免 strip 后产生多余空行）
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 4. 连续空格 → 单个空格
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text


class Agent:

    def __init__(self, client, model, system_prompt, tools, tool_map):

        self.client = client
        self.model = model
        self.tools = tools
        self.tool_map = tool_map

        self.history = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

    def execute_tool(self, tool_call):
        # 兼容 dict（流式模式）和对象（非流式模式）
        if isinstance(tool_call, dict):
            name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])
        else:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

        if name in self.tool_map:
            return self.tool_map[name](**args)

        return f"未知工具: {name}"

    # ---------- 非流式 ----------
    def chat(self, user_input):

        self.history.append({
            "role": "user",
            "content": user_input
        })

        for round_idx in range(MAX_TOOL_ROUNDS):

            tools = self.tools if round_idx < MAX_TOOL_ROUNDS - 1 else []

            try:

                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    messages=self.history,
                    tools=tools,
                    extra_body={"thinking": {"type": "disabled"}},
                )

            except Exception as e:

                logger.error("API 调用失败: %s", e)
                return f"API 调用失败: {e}"

            message = response.choices[0].message

            if not message.tool_calls:

                cleaned = _clean_output(message.content or "")

                # 模型返回空内容时给兜底回复（DeepSeek 偶尔把输出全放进
                # reasoning_content，导致正文为空）
                if not cleaned:
                    logger.warning("⚠️ 模型返回空内容，使用兜底回复")
                    cleaned = "抱歉，暂时无法处理这个请求，请换个方式问问看。"

                self.history.append({
                    "role": "assistant",
                    "content": cleaned
                })

                logger.info("👤 用户: %s", user_input[:200])
                logger.info("🤖 模型: %s", cleaned[:2000])
                return cleaned

            # 保存 assistant 消息（含工具调用）
            self.history.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    }
                    for tc in message.tool_calls
                ]
            })

            for tc in message.tool_calls:

                result = self.execute_tool(tc)

                logger.info("🔧 工具调用: %s | 参数: %s",
                            tc.function.name if hasattr(tc, 'function') else tc["function"]["name"],
                            tc.function.arguments[:500] if hasattr(tc, 'function') else tc["function"]["arguments"][:500])
                logger.info("📋 工具结果: %s", str(result)[:1000])

                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        return "抱歉，暂时无法处理这个请求，请换个方式问问看。"

    # ---------- 流式（收集完整 → 清洗 → 模拟流式输出）----------
    def chat_stream(self, user_input):
        """先收集完整回复，清洗后再逐块 yield，避免空行和思考内容泄露"""

        self.history.append({
            "role": "user",
            "content": user_input
        })

        logger.info("👤 用户: %s", user_input[:200])

        for round_idx in range(MAX_TOOL_ROUNDS):

            tools = self.tools if round_idx < MAX_TOOL_ROUNDS - 1 else []

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    messages=self.history,
                    tools=tools,
                    stream=True,
                    extra_body={"thinking": {"type": "disabled"}},
                )
            except Exception as e:
                yield f"API 调用失败: {e}"
                return

            # —— 第一阶段：静默收集所有 chunk ——
            content_chunks = []
            tool_calls_map = {}
            had_reasoning = False

            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # 跳过思考/推理内容（DeepSeek reasoning_content）
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    had_reasoning = True
                    continue

                # 文本内容：收集但先不输出
                if delta.content:
                    text = delta.content
                    # 检测 DSML/XML 工具调用格式泄露 → 丢弃
                    if '<｜DSML｜' in text or '｜>' in text:
                        continue
                    content_chunks.append(text)

                # 工具调用 delta
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tool_calls_map:
                            tool_calls_map[idx] = {
                                "id": tc_delta.id or "",
                                "function": {"name": "", "arguments": ""}
                            }
                        if tc_delta.id:
                            tool_calls_map[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tool_calls_map[idx]["function"]["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                tool_calls_map[idx]["function"]["arguments"] += tc_delta.function.arguments

            # —— 第二阶段：清洗 ——
            full_content = "".join(content_chunks)
            full_content = _clean_output(full_content)

            # 没有工具调用 → 清洗后模拟流式输出
            if not tool_calls_map:
                # 模型返回空内容时给兜底（DeepSeek 偶尔把输出全放进
                # reasoning_content，导致正文为空）
                if not full_content:
                    logger.warning("⚠️ 流式模型返回空内容 (had_reasoning=%s)，使用兜底回复", had_reasoning)
                    full_content = "抱歉，暂时无法处理这个请求，请换个方式问问看。"

                self.history.append({
                    "role": "assistant",
                    "content": full_content
                })
                logger.info("🤖 模型: %s", full_content[:2000])
                # 模拟流式：逐块 yield，块间加延迟让前端有渐进输出效果
                for i in range(0, len(full_content), STREAM_CHUNK_SIZE):
                    yield full_content[i:i + STREAM_CHUNK_SIZE]
                    time.sleep(STREAM_DELAY)
                return

            # —— 有工具调用 ——
            tool_calls_saved = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                    }
                }
                for tc in tool_calls_map.values()
            ]

            self.history.append({
                "role": "assistant",
                "content": full_content or None,
                "tool_calls": tool_calls_saved,
            })

            # 执行工具（静默，不流式输出中间状态）
            for tc in tool_calls_map.values():
                result = self.execute_tool(tc)
                logger.info("🔧 工具调用: %s | 参数: %s",
                            tc["function"]["name"], tc["function"]["arguments"][:500])
                logger.info("📋 工具结果: %s", str(result)[:1000])
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        # 兜底：永远不会到这里（最后一轮不带工具）
        fallback = "抱歉，暂时查不到相关信息，建议换个关键词或直接去学校官网查询。"
        yield fallback
