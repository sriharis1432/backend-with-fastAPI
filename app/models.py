from pydantic import BaseModel
from typing import Dict, Any, Optional

class PredictRequest(BaseModel):
    input_text: str

class GenerateRequest(BaseModel):
    input_text: str
    prediction_data: Dict[str, Any]
