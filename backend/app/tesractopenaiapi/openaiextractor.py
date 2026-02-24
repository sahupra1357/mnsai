from pdf2image import convert_from_path # type: ignore
from PIL import Image # type: ignore
import pytesseract # type: ignore
from openai import OpenAI
import re
import json
from app.models import Message

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

def process_document_invoice(file_path: str):
    print(f"Processing document at {file_path}...")
    images = convert_from_path(file_path)

    print(f"Extracted {len(images)} pages from the document.")
    for i, image in enumerate(images):
        image.save(f'page_{i}.jpg', 'JPEG')

    print("Extracting text from the document...")
    extracted_text = []
    for i, image in enumerate(images):
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


def process_document_contract(file_path: str):
    print(f"Processing document at {file_path}...")
    images = convert_from_path(file_path)

    print(f"Extracted {len(images)} pages from the document.")
    for i, image in enumerate(images):
        image.save(f'page_{i}.jpg', 'JPEG')

    print("Extracting text from the document...")
    extracted_text = []
    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image)
        extracted_text.append(text)
        print(f"Extracted text from page {i}:")

    if not extracted_text:
        print("No text was extracted from the document.")
        return Message(message="No text was extracted from the document.")
    else:
        print("The document contains the following text:")
        print(extracted_text)
    
        cleaned_array = [re.sub(r'\s+', ' ', string).strip() for string in extracted_text]
        #cleaned_array = [re.sub(r'\n', ' ', string).strip() for string in cleaned_array]

        print(cleaned_array)
        return cleaned_array
        #summary_compiled = summarize_content(extracted_text[0])
        # summary_compiled = " ".join(extracted_text)
        # print("The summary of the document is:",summary_compiled)
        # summary_compiled = re.sub(r'\s+', ' ', summary_compiled).strip()
        # summary_compiled= re.sub(r'\n', ' ', summary_compiled).strip()
        #return summary_compiled

        # json_match = re.search(r'{.*}', summary_compiled, re.DOTALL)
        # print("The JSON extracted from the summary is:",json_match)

        # if json_match:
        #     extracted_json = json_match.group(0)
        #     print("The JSON extracted from the text is:", extracted_json)
        #     #return json.loads(extracted_json)
        #     return extracted_json
        # else:
        #     print("No JSON found in the text.")
        #     return Message(message="No JSON found in the text.")
        

