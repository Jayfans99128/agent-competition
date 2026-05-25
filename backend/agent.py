import json


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

    def chat(self, user_input):

        self.history.append({
            "role": "user",
            "content": user_input
        })

        for _ in range(3):

            try:

                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=500,
                    messages=self.history,
                    tools=self.tools,
                    extra_body={"thinking": {"type": "disabled"}},
                )

            except Exception as e:

                return f"API 调用失败: {e}"

            message = response.choices[0].message

            # 没有工具调用
            if not message.tool_calls:

                self.history.append({
                    "role": "assistant",
                    "content": message.content
                })

                return message.content

            # 保存 assistant 消息
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

            # 执行工具
            for tc in message.tool_calls:

                result = self.execute_tool(tc)

                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        return "达到最大工具调用次数"

    def chat_stream(self, user_input):
        """流式聊天，逐块 yield 内容"""

        self.history.append({
            "role": "user",
            "content": user_input
        })

        for _ in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    max_tokens=500,
                    messages=self.history,
                    tools=self.tools,
                    stream=True,
                    extra_body={"thinking": {"type": "disabled"}},
                )
            except Exception as e:
                yield f"API 调用失败: {e}"
                return

            # 收集流式响应
            content_chunks = []
            tool_calls_map = {}

            for chunk in response:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # 文本内容
                if delta.content:
                    content_chunks.append(delta.content)
                    yield delta.content

                # 工具调用
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

            full_content = "".join(content_chunks)

            # 没有工具调用 — 完成
            if not tool_calls_map:
                self.history.append({
                    "role": "assistant",
                    "content": full_content
                })
                return

            # 有工具调用 — 保存历史
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

            # 执行工具
            for tc in tool_calls_map.values():
                result = self.execute_tool(tc)
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": result,
                })

        yield "达到最大工具调用次数"