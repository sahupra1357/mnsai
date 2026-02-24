from typing import Optional

from pydantic import BaseModel, HttpUrl

# ----------------------------
# Pydantic Models
# ----------------------------

class OCRRequest(BaseModel):
    url: Optional[HttpUrl] = None

class OCRResponse(BaseModel):
    text: str