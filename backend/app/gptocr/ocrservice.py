import asyncio
from typing import List, Tuple

from fastapi import HTTPException
from openai import OpenAI, OpenAIError
from app.core.config import settings
from app.gptocr.logger import logger
from app.gptocr.utilityFunction import retry_with_backoff

# ----------------------------
# OCR Service
# ----------------------------

class OCRService:
    def __init__(self):
        try:
            # self.client = AsyncAzureOpenAI(
            #     azure_endpoint=Settings.AZURE_OPENAI_ENDPOINT,
            #     api_version=Settings.OPENAI_API_VERSION,
            #     api_key=Settings.OPENAI_API_KEY,
            # )
            #self.client = OpenAI(api_key=settings.model_config.OPENAI_API_KEY)
            self.client = OpenAI()
        except Exception as e:
            logger.exception(f"Failed to initialize OpenAI client: {e}")
            raise RuntimeError(f"Failed to initialize OpenAI client: {e}")

    async def perform_ocr_on_batch(self, image_batch: List[Tuple[int, str]]) -> str:
        """
        Perform OCR on a batch of images using OpenAI's API with retry logic.

        Args:
            image_batch (List[Tuple[int, str]]): List of tuples containing page numbers and base64-encoded image URLs.

        Returns:
            str: Extracted text.

        Raises:
            HTTPException: If OCR fails after retries.
        """
        async def ocr_request():
            try:
                messages = self.build_ocr_messages(image_batch)
                logger.info(
                    f"Sending OCR request to OpenAI with {len(image_batch)} images."
                )
                #response = await self.client.chat.completions.create(
                response = self.client.chat.completions.create(
                    model=settings.OPENAI_DEPLOYMENT_ID,
                    #model="gpt-4o",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=4000,
                    top_p=0.95,
                    frequency_penalty=0,
                    presence_penalty=0,
                )
                return self.extract_text_from_response(response)
            except OpenAIError as e:
                if "rate limit" in str(e).lower():
                    raise HTTPException(
                        status_code=429, detail="Rate limit exceeded."
                    )
                else:
                    logger.error(f"OpenAI API error: {e}")
                    raise HTTPException(
                        status_code=502,
                        detail=f"OCR processing failed: {e}",
                    )
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=504,
                    detail="Timeout occurred while communicating with OCR service.",
                )
            except Exception as e:
                logger.exception(f"Unexpected error during OCR processing: {e}")
                raise HTTPException(
                    status_code=500, detail=f"OCR processing failed: {e}"
                )

        return await retry_with_backoff(ocr_request)

    def build_ocr_messages(self, image_batch: List[Tuple[int, str]]) -> List[dict]:
        """
        Build the message payload for the OCR request.

        Args:
            image_batch (List[Tuple[int, str]]): List of tuples containing page numbers and image URLs.

        Returns:
            List[dict]: The message payload.
        """
        system_message = """
                You are an OCR assistant and have ability to extract content from any type of document such as passport, driving license, adhar card, voter id card, green card, citizenship card, birth certificate, invoices, bills, contract, etc.
                Extract all text from the provided images (Describe images as if you're explaining them to a blind person eg: `[Image: In this picture, 8 people are posed hugging each other]`), which are attached to the document. 
                Use markdown formatting for:\n\n- Headings (# for main, ## for sub)\n- Lists (- for unordered, 1. for ordered)\n- Emphasis (* for italics, ** for bold)\n- Links ([text](URL))\n- Tables (use markdown table format)\n\nFor non-text elements, describe them: [Image: Brief description]\n\nMaintain logical flow and use horizontal rules (---) to separate sections if needed. 
                Adjust formatting to preserve readability.\n\nNote any issues or ambiguities at the end of your output.\n\nBe thorough and accurate in transcribing all text content.
                

                ## Steps
                1. **Translation**
                - If the image is not in English, transform and translate the entire document into English.

                2. **Classification**
                - Identify the type of document (e.g., passport, driving license, birth certificate, invoice, electric bill, contract, etc.).

                2. **Extraction**
                - Identify key pieces of information typically present personal informations in documents of type passport, driving license, adhar card, voter id card, green card, citizenship card, birth certificate:
                    - **Personal Information**: Name, address, date
                    - **Identification Number**: Passport number, driving license number, adhar card number, voter id card number, green card number, citizenship card number, birth certificate number.
                    - **Date of Issue**: Date of issue of the document.
                    - **Date of Expiry**: Date of expiry of the document.
                    - **Additional Information**: Any other relevant details present in the document.

                - Identify key pieces of information typically present in invoices and bills:
                    - **Vendor Information**: Name, address, contact details, GSTIN, code.
                    - **Invoice Details**: Invoice number, date of issue, due date.
                    - **Itemized Purchases**: List each item or service provided, including Challn No, Part No/ Item Code, HSN/SAC, description,  quantity, unit price, and total price.
                    - **Payment Terms**: Payment methods, terms for discounts, late fees.
                    - **Total Amount Due**: Including any applicable taxes and additional charges.
                    - **Currency**: Specify the currency in which the transaction is made.
                    - **Identifier** : locate a handwritten number and date stacked in the invoice and tag them to ref no, ref date. 

                3. **Completion**, 
                - Review extracted data for accuracy and completeness.
                - Format the extracted information clearly and systematically.

                # Output Format

                - Provide the extracted information in a bulleted or table format for easy readability.
                - Ensure all relevant details are included and clearly labeled for each category of information.

                # Examples

                - **Example 1**:
                - Name: [Name]
                - Address: [Address]
                - Date of Birth: [Date]
                - Identification Number: [ID Number]
                - Date of Issue: [Date]
                - Date of Expiry: [Date]
                - Additional Information: [Details]

                - **Example 2**:
                - Vendor Name: [Vendor Name]
                - Vendor Address: [Vendor Address]
                - Contact: [Contact Information]
                - Invoice Number: [Invoice Number]
                - Date of Issue: [Date]
                - Due Date: [Due Date]
                - Items:
                    - Item 1: [Item Description, Quantity, Unit Price, Total Price]
                    - Item 2: [Item Description, Quantity, Unit Price, Total Price]
                - Payment Terms: [Terms Description]
                - Total Amount Due: [Total Amount]
                - Currency: [Currency]
                
                # Notes

                - Ensure that translations preserve the meaning and context of the original invoice.
                - Extraction should prioritize accuracy and clarity, maintaining the integrity of financial data.
                - If any information is unclear or missing, note the issue at the end of the output.
                    """

        messages = [
            {
                "role": "system",
                "content": system_message,
            },
            {
                "role": "user",
                "content": "Never skip any context! Convert document as is be creative to use markdown effectively to reproduce the same document by using markdown. Translate image text to markdown sequentially. Preserve order and completeness. Separate images with `---`. No skips or comments. Start with first image immediately.",
            },
        ]

        if len(image_batch) == 1:
            # Batch size = 1: Mention the specific page number
            page_num, img_url = image_batch[0]
            messages.append({
                "role": "user",
                "content": f"Page {page_num}:",
            })
            messages.append({
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": img_url}}
                ],
            })
        else:
            # Batch size >1: Include all page numbers and stress returning page numbers in response
            messages.append({
                "role": "user",
                "content": "Please perform OCR on the following images. Ensure that the extracted text includes the corresponding page numbers.",
            })
            content = []
            for page_num, img_url in image_batch:
                content.append({"type": "text", "text": f"Page {page_num}:"})
                content.append({"type": "image_url", "image_url": {"url": img_url}})
            messages.append({
                "role": "user",
                "content": content,
            })

        return messages

    def extract_text_from_response(self, response) -> str:
        """
        Extract text from the OpenAI API response.

        Args:
            response: The response object from OpenAI API.

        Returns:
            str: The extracted text.

        Raises:
            HTTPException: If no text is extracted.
        """
        if (
            not response.choices
            or not hasattr(response.choices[0].message, "content")
            or not response.choices[0].message.content
        ):
            logger.warning("No text extracted from OCR.")
            raise HTTPException(
                status_code=500, detail="No text extracted from OCR."
            )

        extracted_text = response.choices[0].message.content.strip()
        logger.info(f"Extracted text length: {len(extracted_text)} characters.")
        return extracted_text

# Initialize OCR Service
ocr_service = OCRService()