from fastapi import APIRouter, File, UploadFile, HTTPException, Body
import os
import tempfile
import asyncio
from typing import  Optional
from pydantic import  ValidationError
from app.gptocr.model.gptmodel import OCRRequest, OCRResponse
from app.gptocr.utilityFunction import convert_pdf_to_images_pymupdf, encode_images, create_batches
from app.gptocr.helperFunction import get_pdf_bytes
from app.gptocr.ocrbatchprocess import process_batches, concatenate_texts
from app.gptocr.logger import logger
from app.core.config import settings
from app.api.deps import CurrentUser, SessionDep
import re
from app.models import Extr, ExtrBase, Item
from typing import Any
from sqlmodel import func, select

router = APIRouter(prefix="/gptfiles", tags=["gptfiles"])
# ----------------------------
# API Endpoint
# ----------------------------
@router.post('/ocr', response_model=OCRResponse)
async def ocr_endpoint(
    session: SessionDep,
    file: Optional[UploadFile] = File(None),
    #ocr_request: Optional[OCRRequest] = Body(None),
    current_user: CurrentUser = None,
):
    """
    Perform OCR on a provided PDF file or a PDF from a URL.

    Args:
        file (Optional[UploadFile]): The uploaded PDF file.
        ocr_request (Optional[OCRRequest]): The OCR request containing a PDF URL.

    Returns:
        OCRResponse: The response containing the extracted text.

    Raises:
        HTTPException: If input validation fails or processing errors occur.
    """
    try:
        extr_count = read_extr_count(session=session, current_user=current_user)
        print(f"Extr count is {extr_count}", settings.MAX_EXTR_COUNT)
        if extr_count > settings.MAX_EXTR_COUNT:
            logger.warning("OCR request rejected: maximum number of extractions reached.")
            raise HTTPException(
                status_code=403,
                detail="Maximum number of extractions reached. Please subscribe to use further.",
            )
        
        # Retrieve PDF bytes
        #pdf_bytes = await get_pdf_bytes(file, ocr_request)
        print(f"File is {file}")
        pdf_bytes = await get_pdf_bytes(file)

        # Save PDF bytes to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf_file:
            tmp_pdf_file.write(pdf_bytes)
            tmp_pdf_path = tmp_pdf_file.name
            logger.info(f"Saved PDF to temporary file {tmp_pdf_path}.")

        try:
            # Convert PDF to images using PyMuPDF with multiprocessing
            loop = asyncio.get_event_loop()
            image_bytes_list = await loop.run_in_executor(
                None, convert_pdf_to_images_pymupdf, tmp_pdf_path
            )

            file_extr = ExtrBase(filename=file.filename, pagecount=len(image_bytes_list), owner_id=current_user.id)
            create_extr(extr_in=file_extr, current_user=current_user, session=session)

            # Encode images to base64 data URLs along with page numbers
            image_data_urls = encode_images(image_bytes_list)

            # Create batches for OCR
            batches = create_batches(image_data_urls, settings.BATCH_SIZE)
            #batches = create_batches(image_data_urls, 1)

            # Process OCR batches in parallel
            extracted_texts = await process_batches(batches)

            # Concatenate extracted texts
            final_text = concatenate_texts(extracted_texts)

            if not final_text:
                logger.warning("OCR completed but no text was extracted.")
                raise HTTPException(
                    status_code=500, detail="OCR completed but no text was extracted."
                )
            # else:
            #     logger.info("OCR completed successfully.", final_text)

            #     json_match = re.search(r'{.*}', final_text, re.DOTALL)
            #     print("The JSON extracted from the summary is TS:",json_match)

            #     if json_match:
            #         final_text = json_match.group(0)
            #         #print("The JSON extracted from the text is TS:", final_text)
            #         #logger.info("OCR completed successfully.", final_text)
            return OCRResponse(text=final_text)

        finally:
            # Clean up temporary PDF file
            os.remove(tmp_pdf_path)
            logger.info(f"Deleted temporary PDF file {tmp_pdf_path}.")

    except HTTPException:
        raise
    except ValidationError as ve:
        logger.error(f"Validation error: {ve}")
        raise HTTPException(status_code=422, detail="Invalid request parameters.")
    except Exception as e:
        logger.exception(f"Unhandled exception in /ocr endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during OCR processing.",
        )

def create_extr(
    *, session: SessionDep, current_user: CurrentUser, extr_in: ExtrBase
) -> Any:
    """
    Create new item.
    """
    extr = Extr.model_validate(extr_in, update={"owner_id": current_user.id})
    session.add(extr)
    session.commit()
    session.refresh(extr)
    return extr

def read_extr_count(
    session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Retrieve items.
    """

    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Extr)
        count = session.exec(count_statement).one()
        statement = select(Extr)
        items = session.exec(statement).all()
    else:
        count_statement = (
            select(func.count())
            .select_from(Extr)
            .where(Extr.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
    logger.info(f"Retrieved {count} extractions.")
    return count
