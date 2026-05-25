from backend.config import client, MODEL, SYSTEM_PROMPT, TOOLS
from backend.utils.cli import get_input
from backend.utils.file_operations import list_files, read_file
from backend.skill.search.manager import web_search
from backend.skill.resume_analyzer import resume_analyzer
from backend.agent import Agent

TOOL_MAP = {
    "list_files": list_files,
    "read_file": read_file,
    "resume_analyzer": resume_analyzer,
    "web_search": web_search,
    
}

agent = Agent(client, MODEL, SYSTEM_PROMPT, TOOLS, TOOL_MAP)

print("开始对话，按 Esc 退出\n")

while True:
    user_input = get_input()
    if user_input is None:
        print("退出程序")
        break

    if not user_input.strip():
        continue

    agent.chat(user_input)
