from fastapi import APIRouter, File, UploadFile, HTTPException
import os
from fastapi.responses import JSONResponse
#from app.core.config import settings

from app.googleapi.documentocr import process_document
from app.tesractopenaiapi.openaiextractor import process_document_invoice
from app.tesractopenaiapi.openaiextractor_imgpp import process_invoice


#router = APIRouter()
router = APIRouter(prefix="/files", tags=["uploadfiles"])

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@router.post('/upload')
async def upload_file(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    #file_location = os.path.join(file.filename)

    # implement store in S3 bucket aws or GCP
    with open(file_location, "wb") as f:
        f.write(await file.read())
    print("The document uploaded and I am here")
    dpcument_content = process_document(file_location)
    #return JSONResponse(content={"message": "File uploaded successfully", "file_path": file_location}, status_code=200)
    #return JSONResponse(content={"message": "File uploaded successfully and The document contains the following text: "+ dpcument_content.text, "file_path": file_location}, status_code=200)
    return JSONResponse(content={"message": dpcument_content, "file_path": file_location}, status_code=200)    

@router.post('/uploadts')
async def upload_file_ts(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    #file_location = os.path.join(file.filename)

    # implement store in S3 bucket aws or GCP
    with open(file_location, "wb") as f:
        f.write(await file.read())
    print("The document uploaded and I am here TS")
    dpcument_content = process_document_invoice(file_location)
    #return JSONResponse(content={"message": "File uploaded successfully", "file_path": file_location}, status_code=200)
    return JSONResponse(content={"message": dpcument_content, "file_path": file_location}, status_code=200)    

@router.post('/uploadtspp')
async def upload_file_tspp(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    #file_location = os.path.join(file.filename)

    # implement store in S3 bucket aws or GCP
    with open(file_location, "wb") as f:
        f.write(await file.read())
    print("The document uploaded and I am here TS")
    dpcument_content = process_invoice(file_location)
    #return JSONResponse(content={"message": "File uploaded successfully", "file_path": file_location}, status_code=200)
    return JSONResponse(content={"message": dpcument_content, "file_path": file_location}, status_code=200)    