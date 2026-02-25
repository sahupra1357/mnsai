from typing import Any, Optional

from pydantic import BaseModel, HttpUrl

# ----------------------------
# Pydantic Models
# ----------------------------

class OCRRequest(BaseModel):
    url: Optional[HttpUrl] = None

class OCRResponse(BaseModel):
    text: str

class OCRJsonResponse(BaseModel):
    document_type: str
    data: dict[str, Any]