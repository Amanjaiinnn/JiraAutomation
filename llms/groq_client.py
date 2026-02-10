
import os
from groq import Groq
from dotenv import load_dotenv
load_dotenv()

def get_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))
