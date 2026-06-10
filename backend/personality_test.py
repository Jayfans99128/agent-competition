"""
职业性格测试 —— MBTI 职业性格测试
"""
import json

# MBTI 题目（每题2选1）
# dim: 维度 E/I/S/N/T/F/J/P
# sideA: 选项A对应的极性, sideB: 选项B对应的极性
QUESTIONS = [
    # ===== E / I（外向 / 内向）=====
    {"id": 1,  "dim": "EI", "sideA": "E", "sideB": "I", "text": "周末你更喜欢",
     "optionA": "和朋友出去聚会", "optionB": "自己在家看书或追剧"},
    {"id": 2,  "dim": "EI", "sideA": "I", "sideB": "E", "text": "在团体活动中你通常",
     "optionA": "安静观察，较少主动发言", "optionB": "主动找人聊天，融入圈子"},
    {"id": 3,  "dim": "EI", "sideA": "E", "sideB": "I", "text": "与人交往让你感到",
     "optionA": "充满能量，越聊越兴奋", "optionB": "有点消耗精力，需要独处恢复"},
    {"id": 4,  "dim": "EI", "sideA": "I", "sideB": "E", "text": "你更喜欢的社交方式",
     "optionA": "和一两个好友深度交流", "optionB": "参加热闹的多人活动"},
    {"id": 5,  "dim": "EI", "sideA": "I", "sideB": "E", "text": "遇到问题时你更倾向",
     "optionA": "自己先独立思考", "optionB": "马上找人一起讨论"},

    # ===== S / N（实感 / 直觉）=====
    {"id": 6,  "dim": "SN", "sideA": "S", "sideB": "N", "text": "你更关注",
     "optionA": "具体的事实和细节", "optionB": "整体的概念和未来的可能性"},
    {"id": 7,  "dim": "SN", "sideA": "N", "sideB": "S", "text": "阅读或学习时你更喜欢",
     "optionA": "有想象空间的理论和创意", "optionB": "实实在在的数据和案例"},
    {"id": 8,  "dim": "SN", "sideA": "S", "sideB": "N", "text": "描述事物时你更常说",
     "optionA": "实际情况是怎样的", "optionB": "这件事意味着什么"},
    {"id": 9,  "dim": "SN", "sideA": "N", "sideB": "S", "text": "你更喜欢讨论",
     "optionA": "未来的可能性和新想法", "optionB": "当下的具体问题"},
    {"id": 10, "dim": "SN", "sideA": "S", "sideB": "N", "text": "你更倾向于相信",
     "optionA": "亲眼看到、亲身体验的事", "optionB": "直觉和第六感"},

    # ===== T / F（思考 / 情感）=====
    {"id": 11, "dim": "TF", "sideA": "T", "sideB": "F", "text": "做决定时你更看重",
     "optionA": "逻辑和公平公正", "optionB": "感受和人与人之间的和谐"},
    {"id": 12, "dim": "TF", "sideA": "F", "sideB": "T", "text": "朋友向你倾诉烦恼时你会",
     "optionA": "先安抚情绪，表示理解", "optionB": "帮TA分析问题出在哪"},
    {"id": 13, "dim": "TF", "sideA": "T", "sideB": "F", "text": "你觉得自己更偏向",
     "optionA": "理性果断，对事不对人", "optionB": "感性体贴，照顾他人感受"},
    {"id": 14, "dim": "TF", "sideA": "T", "sideB": "F", "text": "你更常被说成是",
     "optionA": "有主见、讲原则的人", "optionB": "善解人意、好说话的人"},
    {"id": 15, "dim": "TF", "sideA": "F", "sideB": "T", "text": "团队意见不合时你更倾向",
     "optionA": "照顾每个人的感受再决定", "optionB": "按最合理的方案直接定"},

    # ===== J / P（判断 / 感知）=====
    {"id": 16, "dim": "JP", "sideA": "J", "sideB": "P", "text": "你更喜欢的生活方式",
     "optionA": "有计划、有安排、按部就班", "optionB": "灵活随意、随机应变"},
    {"id": 17, "dim": "JP", "sideA": "P", "sideB": "J", "text": "你的桌面或房间通常是",
     "optionA": "东西随手放，有点乱但自己找得到", "optionB": "整洁有序，每样东西有固定位置"},
    {"id": 18, "dim": "JP", "sideA": "J", "sideB": "P", "text": "面对截止日期你通常会",
     "optionA": "提前规划好，按时完成", "optionB": "最后冲刺，赶在截止前做完"},
    {"id": 19, "dim": "JP", "sideA": "J", "sideB": "P", "text": "旅游时你更喜欢",
     "optionA": "做好详细攻略再出发", "optionB": "大概定个方向，到了再说"},
    {"id": 20, "dim": "JP", "sideA": "P", "sideB": "J", "text": "你觉得生活中",
     "optionA": "变化和新意比稳定更重要", "optionB": "稳定和秩序比新鲜感更重要"},
]

QUESTIONS_PER_PAGE = 5

# 16种 MBTI 类型详情
MBTI_TYPES = {
    "ISTJ": {
        "name": "检查员",
        "desc": "严肃、沉稳、负责。做事有条理，注重事实和细节，是可靠的组织者。",
        "careers": ["会计师", "审计师", "法官", "项目经理", "公务员", "银行经理", "行政主管"],
    },
    "ISFJ": {
        "name": "守护者",
        "desc": "温暖、体贴、尽职。默默付出，善于照顾他人，注重传统和安全感。",
        "careers": ["教师", "护士", "社工", "心理咨询师", "医生", "人力资源专员", "图书管理员"],
    },
    "INFJ": {
        "name": "提倡者",
        "desc": "有远见、有使命感、善解人意。追求意义，喜欢帮助他人成长。",
        "careers": ["心理咨询师", "大学教师", "作家", "社会工作者", "人力资源总监", "品牌策划"],
    },
    "INTJ": {
        "name": " architect",
        "desc": "独立、有战略眼光、追求卓越。善于系统思考，喜欢把想法变成现实。",
        "careers": ["科学家", "软件架构师", "战略顾问", "投资分析师", "大学教授", "工程师"],
    },
    "ISTP": {
        "name": "手艺人",
        "desc": "冷静、动手能力强、善于解决实际问题。喜欢探索事物运作原理。",
        "careers": ["机械工程师", "电气工程师", "飞行员", "程序员", "维修技师", "外科医生"],
    },
    "ISFP": {
        "name": "探险家",
        "desc": "温和、友善、有艺术气质。活在当下，注重美感和个人价值。",
        "careers": ["平面设计师", "摄影师", "音乐人", "花艺师", "服装设计师", "厨师"],
    },
    "INFP": {
        "name": "调停者",
        "desc": "理想主义、有创造力、心怀大爱。追求内心的真实和世界的美好。",
        "careers": ["作家", "编辑", "心理咨询师", "艺术家", "大学教师", "非营利组织工作者"],
    },
    "INTP": {
        "name": "逻辑学家",
        "desc": "理性、好奇、善于分析。喜欢构建理论模型，追求知识和逻辑自洽。",
        "careers": ["科学家", "程序员", "数据分析师", "大学教授", "工程师", "哲学家"],
    },
    "ESTP": {
        "name": "企业家",
        "desc": "精力充沛、善于交际、行动力强。喜欢冒险和挑战，懂得抓住机会。",
        "careers": ["销售总监", "创业者", "营销经理", "投资顾问", "体育教练", "记者"],
    },
    "ESFP": {
        "name": "表演者",
        "desc": "热情开朗、乐于助人、是人群中的焦点。喜欢分享和带来快乐。",
        "careers": ["主持人", "演员", "导游", "活动策划", "销售顾问", "幼师"],
    },
    "ENFP": {
        "name": "倡导者",
        "desc": "充满热情、富有创造力、善于鼓励他人。喜欢探索各种可能性。",
        "careers": ["广告策划", "记者", "心理咨询师", "培训师", "品牌经理", "人力资源专员"],
    },
    "ENTP": {
        "name": "辩论家",
        "desc": "机智、思维敏捷、喜欢挑战权威。善于辩论和创新，享受智力博弈。",
        "careers": ["律师", "产品经理", "创业顾问", "市场总监", "记者", "技术总监"],
    },
    "ESTJ": {
        "name": "管理者",
        "desc": "果断、高效、有领导力。注重秩序和规则，是天生的组织者。",
        "careers": ["项目经理", "运营总监", "公务员", "企业高管", "军官", "财务经理"],
    },
    "ESFJ": {
        "name": "关怀者",
        "desc": "热情、负责、善于合作。乐于助人，重视人际关系和团队和谐。",
        "careers": ["教师", "护士", "客服经理", "HR主管", "社区工作者", "培训师"],
    },
    "ENFJ": {
        "name": "主人公",
        "desc": "有魅力、有感染力、善于激励他人。是天生的领导者和导师。",
        "careers": ["培训总监", "销售经理", "心理咨询师", "大学教师", "公关经理", "人力资源总监"],
    },
    "ENTJ": {
        "name": "指挥官",
        "desc": "果断、有远见、善于组织。是天生的领袖，擅长制定战略和带领团队。",
        "careers": ["CEO", "管理顾问", "律师", "项目总监", "投资经理", "政府官员"],
    },
}

DIM_LABELS = {
    "EI": ("外向 E", "内向 I"),
    "SN": ("实感 S", "直觉 N"),
    "TF": ("思考 T", "情感 F"),
    "JP": ("判断 J", "感知 P"),
}

DIM_DESC = {
    "EI": ("你喜欢从外部世界获取能量，善于交际、行动力强", "你喜欢从内心世界获取能量，善于思考、享受独处"),
    "SN": ("你关注具体、实在的信息，注重细节和当下的体验", "你关注整体模式和可能性，富有想象力和创造力"),
    "TF": ("你做决定时更看重逻辑分析和客观原则", "你做决定时更看重个人感受和人际和谐"),
    "JP": ("你喜欢有计划、有条理的生活方式", "你喜欢灵活、开放、随遇而安的生活方式"),
}


def calculate_result(answers):
    """
    answers: { "1": "A", "2": "B", ... }  id -> "A" 或 "B"
    返回 MBTI 四码及类型详情
    """
    scores = {"E": 0, "I": 0, "S": 0, "N": 0, "T": 0, "F": 0, "J": 0, "P": 0}

    for q in QUESTIONS:
        qid = str(q["id"])
        answer = answers.get(qid, "A")
        if answer == "A":
            scores[q["sideA"]] += 1
        else:
            scores[q["sideB"]] += 1

    # 计算四个维度的结果
    e_or_i = "E" if scores["E"] >= scores["I"] else "I"
    s_or_n = "S" if scores["S"] >= scores["N"] else "N"
    t_or_f = "T" if scores["T"] >= scores["F"] else "F"
    j_or_p = "J" if scores["J"] >= scores["P"] else "P"

    mbti_code = e_or_i + s_or_n + t_or_f + j_or_p
    type_info = MBTI_TYPES.get(mbti_code, MBTI_TYPES["INTJ"])

    # 各维度详情
    dim_results = []
    for dim_key, dim_poles in [("EI", (e_or_i, "E", "I")), ("SN", (s_or_n, "S", "N")),
                                ("TF", (t_or_f, "T", "F")), ("JP", (j_or_p, "J", "P"))]:
        winner, a, b = dim_poles
        total = scores[a] + scores[b]
        dim_results.append({
            "dim": dim_key,
            "winner": winner,
            "winner_name": DIM_LABELS[dim_key][0] if winner == dim_key[0] else DIM_LABELS[dim_key][1],
            "scoreA": scores[a],
            "scoreB": scores[b],
            "pctA": round(scores[a] / total * 100) if total > 0 else 50,
            "pctB": round(scores[b] / total * 100) if total > 0 else 50,
            "descA": DIM_DESC[dim_key][0],
            "descB": DIM_DESC[dim_key][1],
        })

    return {
        "mbti_code": mbti_code,
        "type_name": type_info["name"],
        "type_desc": type_info["desc"],
        "careers": type_info["careers"],
        "dimensions": dim_results,
        "scores": scores,
    }
