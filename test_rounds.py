"""
压测脚本 -- 测试对话轮数上限（上下文窗口容量）。

用法：python -u test_rounds.py
"""

import sys
import os
import json
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.config import client, MODEL

SYSTEM_PROMPT = "你是一位就业指导专家。简短回复，每次不超过50字。"

TEST_QUESTIONS = [
    "你好，我是计算机专业大三学生",
    "我想问考研的事情",
    "帮我查2026年工学国家线",
    "考清华需要多少分",
    "国考和省考区别",
    "考研还是就业",
    "简历怎么写",
    "面试怎么自我介绍",
    "Java岗位需要什么技能",
    "产品经理职责",
    "数据分析要学什么",
    "推荐求职网站",
    "第一份工作怎么选",
    "前端要学什么",
    "Python和Java哪个好找工作",
    "深圳有什么科技公司",
    "校招和社招区别",
    "秋招什么时候",
    "春招还有机会吗",
    "怎么进国企",
    "技术面考什么",
    "算法面试准备多久",
    "系统设计怎么准备",
    "四六级重要吗",
    "实习经历少怎么办",
    "项目经验怎么写",
    "职业规划怎么做",
    "转行程序员来得及吗",
    "AI方向前景",
    "嵌入式好不好找",
    "测试工程师发展",
    "运维需要什么技能",
    "网安方向如何",
    "云计算还是大数据",
    "想去外企",
    "腾讯字节哪个好",
    "第一份工作薪资",
    "签三方注意什么",
    "档案户口怎么处理",
    "应届生身份保留多久",
    "三方可以毁约吗",
    "报到证是什么",
    "五险一金包括啥",
    "年终奖几个月",
    "加班多值得去吗",
    "远程办公多吗",
    "自由职业靠谱吗",
    "考公准备什么",
    "事业编和公务员区别",
    "选调生是什么",
    "人才引进政策",
    "创业有补贴吗",
    "创业贷款怎么申请",
    "继续问考研",
    "考研英语怎么复习",
    "考研数学基础",
    "专业课怎么准备",
    "复试怎么准备",
    "调剂系统怎么用",
    "学硕专硕区别",
    "全日制非全区别",
    "需要报辅导班吗",
    "考研时间线",
    "教资怎么考",
    "CPA和ACCA哪个好",
    "软考有用吗",
    "PMP值得考吗",
    "雅思托福哪个有用",
    "想去银行",
    "银行校招流程",
    "证券从业怎么考",
    "基金从业考试",
    "保险行业前景",
    "事务所好进吗",
    "四大招人要求",
    "怎么做产品经理",
    "产品经理能力",
    "UI设计师前景",
    "新媒体运营怎么做",
    "电商运营日常",
    "游戏行业好进吗",
    "游戏策划技能",
    "怎么做数据分析",
    "数据分析学历要求",
    "机器学习怎么入门",
    "算法面考什么",
    "怎么做全栈",
    "全栈要学什么",
    "Go语言好找工作吗",
    "C++岗位多吗",
    "Rust有前途吗",
    "Vue还是React",
    "后端选什么框架",
    "数据库学哪些",
    "Redis和MySQL区别",
    "微服务是什么",
    "Docker和K8s要学吗",
    "Linux基础重要吗",
    "想去大厂",
    "大厂面试流程",
    "笔试考什么",
    "简历写期望薪资吗",
    "面试穿什么",
    "面试紧张怎么办",
    "没有offer焦虑",
    "秋招投多少简历",
    "收到offer注意什么",
    "三方违约金多少",
    "车联网方向如何",
    "自动驾驶技术栈",
    "智能座舱是什么",
    "新能源汽车前景",
    "电池工程师专业",
    "嵌入式软件工程师",
    "硬件工程师前景",
    "FPGA好找工作吗",
    "芯片行业缺人吗",
    "半导体行业前景",
]


def main():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    results = []

    print(f"[INFO] Model: {MODEL}", flush=True)
    print(f"[INFO] Questions: {len(TEST_QUESTIONS)}", flush=True)
    print(f"{'Round':<6} {'PromptTok':<10} {'CompTok':<9} {'TotalTok':<9} {'Time':<7} {'Status'}", flush=True)
    print("-" * 70, flush=True)

    for i, question in enumerate(TEST_QUESTIONS):
        round_num = i + 1
        messages.append({"role": "user", "content": question})

        try:
            start = time.time()
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=100,
                messages=messages,
                extra_body={"thinking": {"type": "disabled"}},
            )
            elapsed = time.time() - start

            reply = resp.choices[0].message.content or ""
            usage = resp.usage
            prompt_tok = usage.prompt_tokens
            comp_tok = usage.completion_tokens
            total_tok = usage.total_tokens

            messages.append({"role": "assistant", "content": reply})

            reply_short = reply[:35].replace("\n", " ")
            print(f"{round_num:<6} {prompt_tok:<10} {comp_tok:<9} {total_tok:<9} {elapsed:.1f}s   OK  {reply_short}", flush=True)

            results.append({"round": round_num, "prompt": prompt_tok, "completion": comp_tok, "total": total_tok, "time": elapsed})

        except Exception as e:
            error_msg = str(e)[:100]
            print(f"{round_num:<6} FAILED     {error_msg}", flush=True)
            print(flush=True)
            print("========== RESULT ==========", flush=True)
            print(f"Max rounds: {round_num - 1}", flush=True)
            print(f"Failed at round {round_num}", flush=True)
            print(f"Error: {error_msg}", flush=True)
            if results:
                last = results[-1]
                print(f"Last OK: round {last['round']}, total_tokens={last['total']}", flush=True)
            return

    # 全部完成
    print(flush=True)
    print("========== RESULT ==========", flush=True)
    print(f"Completed {len(TEST_QUESTIONS)} rounds, no limit hit", flush=True)
    if results:
        last = results[-1]
        print(f"Final: total_tokens={last['total']}", flush=True)


if __name__ == "__main__":
    main()