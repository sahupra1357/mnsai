from typing import  Optional

import requests
from fastapi import HTTPException, UploadFile
from app.gptocr.model.gptmodel import OCRRequest
from app.gptocr.logger import logger

# ----------------------------
# Helper Functions for API Endpoint
# ----------------------------

async def get_pdf_bytes(
    file: Optional[UploadFile],
    #ocr_request: Optional[OCRRequest],
) -> bytes:
    """
    Retrieve PDF bytes from an uploaded file or a URL.

    Args:
        file (Optional[UploadFile]): The uploaded PDF file.
        ocr_request (Optional[OCRRequest]): The OCR request containing a PDF URL.

    Returns:
        bytes: The PDF content.

    Raises:
        HTTPException: If retrieval fails or input is invalid.
    """
    print(file, "at the start of get_pdf_bytes")
    # if not file and not ocr_request:
    #     logger.warning("No PDF file or URL provided in the request.")
    #     raise HTTPException(status_code=400, detail="No PDF file or URL provided.")

    # if file and ocr_request and ocr_request.url:
    #     logger.warning("Both file and URL provided in the request; only one is allowed.")
    #     raise HTTPException(
    #         status_code=400, detail="Provide either a file or a URL, not both."
    #     )

    if file:
        return await read_uploaded_file(file)
    # else:
    #     return download_pdf(ocr_request.url)

async def read_uploaded_file(file: UploadFile) -> bytes:
    """
    Read bytes from an uploaded file.

    Args:
        file (UploadFile): The uploaded file.

    Returns:
        bytes: The file content.

    Raises:
        HTTPException: If the file is invalid or reading fails.
    """
    #if file.content_type != "application/pdf":
    if file.content_type not in["application/pdf", "image/jpeg", "image/png"]:
        logger.warning(f"Uploaded file has incorrect content type: {file.content_type}")
        raise HTTPException(
            status_code=400, detail="Uploaded file is not a PDF/JPEG/PNG."
        )
    try:
        pdf_bytes = await file.read()
        if not pdf_bytes:
            logger.warning("Uploaded PDF file is empty.")
            raise HTTPException(
                status_code=400, detail="Uploaded PDF file is empty."
            )
        logger.info(f"Read uploaded PDF file, size: {len(pdf_bytes)} bytes.")
        #logger.info(f"Read uploaded PDF file, size: {(pdf_bytes)} bytes.")
        return pdf_bytes
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=400, detail=f"Failed to read uploaded file: {e}"
        )


def download_pdf(url: str) -> bytes:
    """
    Download a PDF file from the specified URL.

    Args:
        url (str): The URL of the PDF.

    Returns:
        bytes: The content of the PDF.

    Raises:
        HTTPException: If the download fails or the content is not a PDF.
    """
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "application/pdf" not in content_type:
            logger.warning(f"Invalid content type: {content_type} for URL: {url}")
            raise HTTPException(
                status_code=400, detail="URL does not point to a valid PDF file."
            )
        logger.info(f"Downloaded PDF from {url}, size: {len(response.content)} bytes.")
        return response.content
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while downloading PDF from {url}.")
        raise HTTPException(
            status_code=504, detail="Timeout occurred while downloading the PDF."
        )
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error while downloading PDF from {url}: {e}")
        raise HTTPException(
            status_code=400, detail=f"HTTP error occurred: {e}"
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error while downloading PDF from {url}: {e}")
        raise HTTPException(
            status_code=400, detail=f"Failed to download PDF: {e}"
        )