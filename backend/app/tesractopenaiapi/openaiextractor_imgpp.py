from pdf2image import convert_from_path # type: ignore
from PIL import Image # type: ignore
import pytesseract # type: ignore
from openai import OpenAI # type: ignore
import re
import json
from app.models import Message
# import cv2 # type: ignore
import numpy as np # type: ignore


def summarize_content(content, character_limit=500):
        client = OpenAI()
        prompt = (
            f"You are an AI assistant tasked with extracting relavant information only" # from the utility bill. "
            f"Please provide a concise summary in {character_limit} characters or less in JSON form. Reply with only the answer in JSON form and include no other commentary:"
        )
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content}]
            )
            summary = response.choices[0].message.content
            return summary
        except Exception as e:
            print(f"An error occurred during summarization: {e}")
            return None

def process_invoice(file_path: str):
    print(f"Processing document at {file_path}...")
    images = convert_from_path(file_path)

    print(f"Extracted {len(images)} pages from the document.")
    for i, image in enumerate(images):
        image.save(f'page_{i}.jpg', 'JPEG')

    # Preprocess the images
    print("Preprocessing the images...")
    #processed_images = image_preprocessing(images)
    processed_images = images

    print("Extracting text from the document...")
    extracted_text = []
    #for i, image in enumerate(images):
    for i, image in enumerate(processed_images):
        text = pytesseract.image_to_string(image)
        extracted_text.append(text)
        print(f"Extracted text from page {i}:")

    if not extracted_text:
        print("No text was extracted from the document.")
        return Message(message="No text was extracted from the document.")
    else:
        print("The document contains the following text TS:")
        print(extracted_text)
        
        summary_compiled = summarize_content(extracted_text[0])

        json_match = re.search(r'{.*}', summary_compiled, re.DOTALL)
        print("The JSON extracted from the summary is TS:",json_match)

        if json_match:
            extracted_json = json_match.group(0)
            print("The JSON extracted from the text is TS:", extracted_json)
            return json.loads(extracted_json)
            #return extracted_json
        else:
            print("No JSON found in the text.")
            return Message(message="No JSON found in the text.")

        # return summary_compiled
        # #return summary_compiled
        # return extracted_text        

# def image_preprocessing(images):

#     processed_images = []
#     for image in images:
#         numpy_image = np.array(image)
#         #image = cv2.imread(image)

#         # Preprocess the image
#         gray_image = cv2.cvtColor(numpy_image, cv2.COLOR_BGR2GRAY)
#         denoised_image = cv2.fastNlMeansDenoising(gray_image)
#         _, binary_image = cv2.threshold(denoised_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
#         coords = np.column_stack(np.where(binary_image > 0))
#         angle = cv2.minAreaRect(coords)[-1]
#         if angle < -45:
#             angle = -(90 + angle)
#         else:
#             angle = -angle

#         (h, w) = binary_image.shape[:2]
#         center = (w // 2, h // 2)
#         M = cv2.getRotationMatrix2D(center, angle, 1.0)
#         rotated = cv2.warpAffine(binary_image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)    
#         processed_images.append(rotated)
#     return processed_images

