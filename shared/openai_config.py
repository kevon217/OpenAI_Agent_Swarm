from shared.settings import Settings
from openai import OpenAI

from dotenv import load_dotenv
import os

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def get_openai_client():
    settings = Settings()
    return OpenAI(api_key=settings.OPENAI_API_KEY)
