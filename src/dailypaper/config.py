import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Paths:
    root: Path = Path(__file__).resolve().parents[2]  # ~/dailypaper
    data: Path = root / "data"
    raw: Path = data / "raw"
    db: Path = data / "db" / "dailypaper.sqlite3"
    logs: Path = root / "logs"

@dataclass(frozen=True)
class Settings:
    hf_api_base: str = "https://huggingface.co/api/daily_papers?date="
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "").strip()
    model: str = os.environ.get("OPENAI_MODEL", "gpt-5.2")
    
    taxonomy: tuple = (
        "Robotics",
        "LLM",
        "Multimodal",
        "Vision",
        "RL",
        "Systems",
        "Audio",
        "Theory",
        "Other",
    )

PATHS = Paths()
SETTINGS = Settings()
