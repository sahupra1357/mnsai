from fastapi import APIRouter, File, UploadFile, HTTPException
import os
from fastapi.responses import JSONResponse
#from app.core.config import settings

#from app.googleapi.documentocr import process_document
#from app.tesractopenaiapi.openaiextractor import process_document_invoice

#router = APIRouter()
router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), 'output')

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

@router.post('/upload')
#async def upload_file(file: UploadFile = File(...)):
async def process_document_invoice(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    #output_location = os.path.join(OUTPUT_FOLDER, file.filename.replace(".pdf", ".txt"))
    #file_location = os.path.join(file.filename)

    # implement store in S3 bucket aws or GCP
    with open(file_location, "wb") as f:
        f.write(await file.read())
    print("The document uploaded and I am here")
    
    #dpcument_content = process_document(file_location)
    dpcument_content = process_document_invoice(file_location)
    #dpcument_content = {"message":"I am the return value what is the problem???"}
    # with open(output_location, "w") as fout:
    #     for paragraph in dpcument_content:
    #         fout.write(paragraph)
    #         fout.write("\n\n")
    #         #fout.write(dpcument_content)

    #return JSONResponse(content={"message": "File uploaded successfully", "file_path": file_location}, status_code=200)
    #return JSONResponse(content={"message": "File uploaded successfully and The document contains the following text: "+ dpcument_content.text, "file_path": file_location}, status_code=200)    
    #print("The document contains the following text: ", dpcument_content)
    #return JSONResponse(content={"message": "File uploaded successfully and The document contains the following text: "+ dpcument_content, "file_path": file_location}, status_code=200)    
    ##return JSONResponse(content={"message": dpcument_content, "file_path": file_location}, status_code=200)    
    #return " ".join(dpcument_content)
    return dpcument_content


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
    #summary_compiled = {"message":"I am the return value what is the problem???"}
    #summary_compiled = "I am the return value what is the problem???"
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
        
        summary_compiled = summarize_content(extracted_text[0])
        # summary_compiled = " ".join(extracted_text)
        # print("The summary of the document is:",summary_compiled)
        summary_compiled = re.sub(r'\s+', ' ', summary_compiled).strip()
        summary_compiled= re.sub(r'\n', ' ', summary_compiled).strip()
        # summary_compiled = summarize_content(summary_compiled)

        json_match = re.search(r'{.*}', summary_compiled, re.DOTALL)
        print("The JSON extracted from the summary is:",json_match)

        if json_match:
            extracted_json = json_match.group(0)
            print("The JSON extracted from the text is:", extracted_json)
            return json.loads(extracted_json)
            #return extracted_json
        else:
            print("No JSON found in the text.")
            return Message(message="No JSON found in the text.")

        # return summary_compiled
        # #return summary_compiled
        # return extracted_text
