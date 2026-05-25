from backend.config import TOOLS
from backend.utils.file_operations import list_files, read_file
from backend.skill.search.manager import web_search
from backend.skill.resume_analyzer.resume_analyzer import analyze as resume_analyzer

TOOL_MAP = {
    "list_files": list_files,
    "read_file": read_file,
    "resume_analyzer": resume_analyzer,
    "web_search": web_search,
}
