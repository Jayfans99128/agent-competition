from backend.config import TOOLS
from backend.utils.file_operations import list_files, read_file
from backend.skill.search.manager import web_search
from backend.skill.resume_analyzer.resume_analyzer import analyze as resume_analyzer
from backend.knowledge_base import query_knowledge_base, query_kaoyan_scores, query_guokao_scores, query_kaoyan_school
from backend.doubao_client import query_doubao
from backend.knowledge_base.kaoyan_manager import query_kaoyan_data
from backend.ocr_tools import ocr_image_from_url, ocr_image_from_file, ocr_image_from_bytes
from backend.knowledge_base.kaoyan_parser import parse_kaoyan_scores, query_kaoyan_scores_with_parser

TOOL_MAP = {
    "list_files": list_files,
    "read_file": read_file,
    "resume_analyzer": resume_analyzer,
    "web_search": web_search,
    "query_knowledge_base": query_knowledge_base,
    "query_kaoyan_scores": query_kaoyan_scores,
    "query_guokao_scores": query_guokao_scores,
    "query_kaoyan_school": query_kaoyan_school,
    "query_doubao": query_doubao,
    "query_kaoyan_data": query_kaoyan_data,
    "ocr_image_from_url": ocr_image_from_url,
    "ocr_image_from_file": ocr_image_from_file,
    "ocr_image_from_bytes": ocr_image_from_bytes,
    "parse_kaoyan_scores": parse_kaoyan_scores,
    "query_kaoyan_scores_with_parser": query_kaoyan_scores_with_parser,
}