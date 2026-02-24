import asyncio
from typing import List, Tuple

from app.gptocr.logger import logger
from app.gptocr.ocrservice import ocr_service

async def process_batches(batches: List[List[Tuple[int, str]]]) -> List[str]:
    """
    Process each batch of images for OCR in parallel.

    Args:
        batches (List[List[Tuple[int, str]]]): List of image batches with page numbers.

    Returns:
        List[str]: Extracted texts from each batch.
    """
    tasks = [
        asyncio.create_task(ocr_service.perform_ocr_on_batch(batch))
        for batch in batches
    ]
    extracted_texts = await asyncio.gather(*tasks, return_exceptions=False)
    return extracted_texts

def concatenate_texts(texts: List[str]) -> str:
    """
    Concatenate a list of texts with double newlines.

    Args:
        texts (List[str]): List of text snippets.

    Returns:
        str: The concatenated text.
    """
    final_text = "\n\n".join(texts)
    logger.info(f"Total extracted text length: {len(final_text)} characters.")
    return final_text
