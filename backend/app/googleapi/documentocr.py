from typing import Optional

from google.api_core.client_options import ClientOptions # type: ignore
#from google.auth.credentials import Credentials # type: ignore
from google.cloud import documentai  # type: ignore
from openai import OpenAI # type: ignore
import re
import json

# TODO(developer): Uncomment these variables before running the sample.
project_id = "strategic-guru-444919-s3"
location = "us" # Format is "us" or "eu"
processor_id = "9728391baa213d76" # Create processor before running sample
#file_path = "/home/mxmanu1234/100149908178-095737680706-.PDF"
mime_type = "application/pdf" # Refer to https://cloud.google.com/document-ai/docs/file-types for supported file types
field_mask = "text,entities,pages.pageNumber"  # Optional. The fields to return in the Document object.
# processor_version_id = "YOUR_PROCESSOR_VERSION_ID" # Optional. Processor version to use


def process_document_sample(
    project_id: str,
    location: str,
    processor_id: str,
    file_path: str,
    mime_type: str,
    field_mask: Optional[str] = None,
    processor_version_id: Optional[str] = None,
) -> None:
    print("The document uploaded successfully and about to call the process_document_sample")
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    print("1111111111111111")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    print("2222222222222222")

    if processor_version_id:
        print("3333333333333333")
        # The full resource name of the processor version, e.g.:
        # `projects/{project_id}/locations/{location}/processors/{processor_id}/processorVersions/{processor_version_id}`
        name = client.processor_version_path(
            project_id, location, processor_id, processor_version_id
        )
    else:
        print("4444444444444444")
        # The full resource name of the processor, e.g.:
        # `projects/{project_id}/locations/{location}/processors/{processor_id}`
        name = client.processor_path(project_id, location, processor_id)

    print("5555555555555555")
    # Read the file into memory
    with open(file_path, "rb") as image:
        image_content = image.read()

    # Load binary data
    raw_document = documentai.RawDocument(content=image_content, mime_type=mime_type)

    # For more information: https://cloud.google.com/document-ai/docs/reference/rest/v1/ProcessOptions
    # Optional: Additional configurations for processing.
    process_options = documentai.ProcessOptions(
        # Process only specific pages
        individual_page_selector=documentai.ProcessOptions.IndividualPageSelector(
            pages=[1]
        )
    )

    # Configure the process request
    request = documentai.ProcessRequest(
        name=name,
        raw_document=raw_document,
        field_mask=field_mask,
        process_options=process_options,
    )

    result = client.process_document(request=request)

    # For a full list of `Document` object attributes, reference this page:
    # https://cloud.google.com/document-ai/docs/reference/rest/v1/Document
    document = result.document

    # Read the text recognition output from the processor
    print("The document contains the following text:")
    print(document.text)

    summary_compiled = summarize_content(document.text)
    #return document
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



#process_document_sample(project_id,location,processor_id,file_path,mime_type,field_mask)

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
        
def process_document(file_path: str):
    return process_document_sample(project_id,location,processor_id,file_path,mime_type,field_mask)