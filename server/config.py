from pathlib import Path
from pydantic import BaseModel


UPLOAD_DIR = Path('./uploads')
OUTPUT_DIR = Path('./outputs')

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================================
# MODELS
# ============================================================================

class GenerateRequest(BaseModel):
    filename: str
    target: str = "stm32f4"
    name: str = "network"