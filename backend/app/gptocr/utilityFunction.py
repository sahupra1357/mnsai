import asyncio
import base64
from typing import Any, Callable, List, Tuple

import fitz  # PyMuPDF
from fastapi import HTTPException
from concurrent.futures import ProcessPoolExecutor, as_completed
from app.gptocr.logger import logger
from app.core.config import settings

# ----------------------------
# Utility Functions
# ----------------------------

def convert_page_to_image(args: Tuple[str, int, int]) -> Tuple[int, bytes]:
    """
    Convert a single PDF page to PNG image bytes using PyMuPDF.

    Args:
        args (Tuple[str, int, int]): A tuple containing:
            - pdf_path (str): Path to the PDF file.
            - page_num (int): Page number to convert (0-based).
            - zoom (int): Zoom factor for rendering.

    Returns:
        Tuple[int, bytes]: A tuple of page number and image bytes.

    Raises:
        Exception: If rendering fails.
    """
    pdf_path, page_num, zoom = args
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)
        matrix = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix)
        image_bytes = pix.tobytes("png")
        logger.debug(
            f"Rendered page {page_num + 1}/{doc.page_count}, size: {len(image_bytes)} bytes."
        )
        doc.close()
        return (page_num + 1, image_bytes)  # Page numbers start at 1
    except Exception as e:
        logger.error(f"Error rendering page {page_num + 1}: {e}")
        raise

def convert_pdf_to_images_pymupdf(pdf_path: str, zoom: int = 2) -> List[Tuple[int, bytes]]:
    """
    Convert a PDF file to a list of PNG image bytes using PyMuPDF with multiprocessing.

    Args:
        pdf_path (str): Path to the PDF file.
        zoom (int): Zoom factor for rendering.

    Returns:
        List[Tuple[int, bytes]]: List of tuples containing page number and PNG image bytes.

    Raises:
        HTTPException: If conversion fails.
    """
    try:
        doc = fitz.open(pdf_path)
        page_count = doc.page_count
        doc.close()
        logger.info(f"PDF loaded with {page_count} pages.")

        # Prepare arguments for each page
        args_list = [(pdf_path, i, zoom) for i in range(page_count)]

        image_bytes_list: List[Tuple[int, bytes]] = []  # List of (page_num, image_bytes)

        with ProcessPoolExecutor(max_workers=settings.MAX_CONCURRENT_PDF_CONVERSION) as executor:
        #with ProcessPoolExecutor(max_workers=4) as executor:
            # Submit all tasks
            future_to_page = {
                executor.submit(convert_page_to_image, args): args[1]
                for args in args_list
            }

            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    page_num_result, image_bytes = future.result()
                    image_bytes_list.append((page_num_result, image_bytes))
                except Exception as e:
                    logger.error(f"Failed to convert page {page_num + 1}: {e}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to convert page {page_num + 1} to image.",
                    )

        # Sort the list by page number to maintain order
        image_bytes_list.sort(key=lambda x: x[0])

        logger.info(f"Converted PDF to {len(image_bytes_list)} images using PyMuPDF.")
        return image_bytes_list

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error converting PDF to images with PyMuPDF: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to convert PDF to images: {e}"
        )

def encode_image_to_base64(image_bytes: bytes) -> str:
    """
    Encode image bytes to a base64 data URL.

    Args:
        image_bytes (bytes): The image content.

    Returns:
        str: Base64 encoded data URL.

    Raises:
        HTTPException: If encoding fails.
    """
    try:
        base64_str = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:image/png;base64,{base64_str}"
        logger.info(
            f"Encoded image to base64 data URL, length: {len(data_url)} characters."
            #f"Encoded image to base64 data URL, length: {data_url} characters."
        )
        return data_url
    except Exception as e:
        logger.error(f"Error encoding image to base64: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to encode image to base64."
        )

def encode_images(image_bytes_list: List[Tuple[int, bytes]]) -> List[Tuple[int, str]]:
    """
    Encode a list of image bytes to base64 data URLs along with their page numbers.

    Args:
        image_bytes_list (List[Tuple[int, bytes]]): List of tuples containing page numbers and image bytes.

    Returns:
        List[Tuple[int, str]]: List of tuples containing page numbers and base64-encoded image URLs.
    """
    encoded_urls = [(page_num, encode_image_to_base64(img_bytes)) for page_num, img_bytes in image_bytes_list]
    logger.info(f"Encoded {len(encoded_urls)} images to base64 data URLs.")
    return encoded_urls

def create_batches(items: List[Tuple[int, str]], batch_size: int) -> List[List[Tuple[int, str]]]:
    """
    Split a list of items into batches.

    Args:
        items (List[Tuple[int, str]]): The list of tuples containing page numbers and image URLs.
        batch_size (int): The maximum size of each batch.

    Returns:
        List[List[Tuple[int, str]]]: A list of batches.
    """
    batches = [items[i : i + batch_size] for i in range(0, len(items), batch_size)]
    logger.info(
        f"Divided images into {len(batches)} batches of up to {batch_size} images each."
    )
    return batches

async def retry_with_backoff(
    func: Callable[..., Any],
    max_retries: int = 10,
    base_delay: int = 1,
    max_delay: int = 120,
    *args,
    **kwargs
) -> Any:
    """
    Retry a coroutine function with exponential backoff.

    Args:
        func (Callable): The coroutine function to retry.
        max_retries (int): Maximum number of retries.
        base_delay (int): Initial delay in seconds.
        max_delay (int): Maximum delay in seconds.
        *args: Positional arguments for the function.
        **kwargs: Keyword arguments for the function.

    Returns:
        Any: The result of the function if successful.

    Raises:
        HTTPException: If all retries fail.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except HTTPException as he:
            if he.status_code == 429:
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                logger.warning(
                    f"Rate limit encountered. Retrying in {delay} seconds... (Attempt {attempt}/{max_retries})"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"HTTPException during retry: {he.detail}")
                raise
        except asyncio.TimeoutError:
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            logger.warning(
                f"Timeout. Retrying in {delay} seconds... (Attempt {attempt}/{max_retries})"
            )
            await asyncio.sleep(delay)
        except Exception as e:
            logger.exception(f"Unexpected error during retry: {e}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred during processing.",
            )
    logger.error("Exceeded maximum retries.")
    raise HTTPException(
        status_code=429, detail="Maximum retry attempts exceeded."
    )
