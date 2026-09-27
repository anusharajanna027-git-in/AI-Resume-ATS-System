import os
from pathlib import Path

#importing the dotenv here for to load the api keys here# 
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# settingup out app tiltle and all
APP_TITLE = 'ATS RESUME ANALYSER API'
APP_VERSION = '1.0.0'
APP_DESCRIPTION = 'analyse resumes against job description using nlp + ml'


#Cors-Cross Origin Resource Sharing-sometime the web browser could not allows directly a call from any origin to our website so we need to sepcify the origins that our website will aloows the origins 
ALLOWED_ORIGINS = [
    "https://ai-resume-ats-system-vktbzzbhvrqmbdtasdjrkr.streamlit.app/"
]
 
#file 
MAX_FILE_SIZE_MB=5
MAX_FILE_SIZE_BYTES=MAX_FILE_SIZE_MB*1024*1024

#Supported MIME types and their short names
SUPPORTED_MIME_TYPES = {
    'application/pdf': 'pdf',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
}

SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

SPACY_MODEL_PRIMARY="en_core_web_md" #better accuracy
SPACY_MODEL_SECONDARY="en_core_web_sm" 
SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")

# Score component weights — this is business logic treated as config
SCORE_WEIGHTS = {
    "formatting": 20, "keywords": 25, "content": 25,
    "skill_validation": 15, "ats_compatibility": 15,
}

JD_KEYWORD_WEIGHT=0.6
JD_SEMANTIC_WEIGHT=0.4

SUPABASE_URL       = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY       = os.getenv('SUPABASE_KEY', '')          # service_role — DB writes (bypasses RLS)
SUPABASE_ANON_KEY  = os.getenv('SUPABASE_ANON_KEY', '')     # public anon — frontend auth calls
SUPABASE_JWT_SECRET= os.getenv('SUPABASE_JWT_SECRET', '')   # used by backend to verify access tokens
GROQ_API_KEY       = os.getenv('GROQ_API_KEY', '')


