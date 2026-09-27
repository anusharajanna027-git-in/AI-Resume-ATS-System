# here we discuss the file parsing criterias(how the parsing works) that our system will allow only like pdf and docx ...
import io
import magic# which is used to check the uploaded files(which is pdf or not) are allowed or not for what we already written the file formats forms 
from typing import Tuple, Optional

#importing the parsers
import pdfplumber # helps to parse the pdf
from docx import Document #hepls to parse the documents
import PyPDF2 # this is we choose as for fallback for pdf parser if plumber will failed then pypdf2 will work.this is like backup

# importing all the errors  and logs from utils file we already defined the errors there inside the file_utils file
from backend.utils.file_utils import(
    FileParsingError,
    TextExtractionError,
    FileUploadError,
    log_error,
    log_warning,
    log_info,
    with_fallback
)
 # importing the files related modlues from config.py
from backend.core.config import(
    MAX_FILE_SIZE_MB,
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_MIME_TYPES,

)

#we need to define the 2 exception  classes of error if user uploaded a resume which is not the file formate of what we defined the fileformats .The file should be uploaded as perfectly suits to of what we defined the file types and file size and file size bytes
class FileParsingError(Exception):
    pass

class FileValidationError(Exception):  # the uploaded file it would suits our defined file format but the content or info within it can't be extracted -then we have validation error
    pass
  
def validate_file(file_data:bytes, filename:str)->Tuple[bool, str, Optional[str]]:
    # to check the file size if uploaded file size is greater then the what we defined the max file size then in this case we define a logic here
    file_size_bytes = len(file_data)
    if file_size_bytes > MAX_FILE_SIZE_BYTES:
        size_mb = file_size_bytes / (1024 * 1024) # this is claculating the the uploaded file that suits the defined file mb file
        return False, (
            f'File size ({size_mb:.2f} MB) exceeds the maximum of {MAX_FILE_SIZE_MB} MB. '
            'Please upload a smaller file or compress your resume.'
        ), None
    # if user upload the file equals to zero means no content in the file
    if file_size_bytes==0:
        return False, 'uploade file is empty...please check the file you have uploaded and try again'


    # to check (used magic: it will check internally which file is this and about the content which fits or not for our defined file formats and sizes) the uploaded file which is currect or not means crt file type with size
    try:
        mime_type=magic.from_buffer(file_data, mime=True)
    except Exception as e:
        return False, f"error deteminin the file type : {e}", None
      # to check if the uploaded files are comes around the already defined SUPPORTED_MIME_TYPES
    if mime_type not in SUPPORTED_MIME_TYPES:
        supported=', '.join(SUPPORTED_MIME_TYPES.keys()).upper()
        return False, (
            f'Unsupported file type: {mime_type}. '
            f'Please upload one of: {supported}.'
        ), None
    
    

    return True, '', SUPPORTED_MIME_TYPES[mime_type]

# the pdf contains the 2 sections 1. Visible section=> in this sections extract the the tiltles of experiences, location  ect  2. Annotation section=>in this section  if any hyperlink present in the pdf that to be extracted so for this we define a class 
def _extract_pdf_hyperlinks(file_data: bytes) -> str:
    urls = []
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_data))
        for page in reader.pages:
            if '/Annots' not in page:
                continue
            for annot_ref in page['/Annots']:
                try:
                    annot = annot_ref.get_object()
                    if annot.get('/Subtype') != '/Link':
                        continue
                    action = annot.get('/A', {})
                    uri = action.get('/URI', '')
                    if uri and isinstance(uri, (str, bytes)):
                        # PyPDF2 may return bytes for URI values
                        if isinstance(uri, bytes):
                            uri = uri.decode('utf-8', errors='ignore')
                        uri = uri.strip()
                        if uri.startswith('http'):
                            urls.append(uri)
                except Exception:
                    pass
    except Exception:
        pass
    return '\n'.join(urls)

# pdfplumber => to extract the "complex" pdfs
def _extract_pdf_with_pdfplumber(file_data: bytes) -> str:
    text = ''
    with pdfplumber.open(io.BytesIO(file_data)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n'

    if not text.strip():
        raise TextExtractionError(
            'pdfplumber extracted no text',
            user_message='No text could be extracted from the PDF.'
        )
    
    hyperlinks = _extract_pdf_hyperlinks(file_data)
    if hyperlinks:
        text = text.strip() + '\n' + hyperlinks

    return text.strip()

#extract the pdf with pypdf2
def _extract_pdf_with_pypdf2(file_data: bytes) -> str:
    text = ''
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data))
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + '\n'

    if not text.strip():
        raise TextExtractionError(
            'PyPDF2 extracted no text',
            user_message='No text could be extracted from the PDF.'
        )

    hyperlinks = _extract_pdf_hyperlinks(file_data)
    if hyperlinks:
        text = text.strip() + '\n' + hyperlinks

    return text.strip()

# normal extraction of pdf 
def extract_text_from_pdf(file_data: bytes) -> str:
    try: 
        result, used_fallback=with_fallback(
        _extract_pdf_with_pdfplumber, # if pdfplumber is not availabel then fallback we use called pypdf2
        _extract_pdf_with_pypdf2, 
        file_data, 
        log_fallback=True
    )
      # if using  used_fallback for if the pdfplumber will fails to extract the pdf then for that we use a fallback pypdf2
        if used_fallback:
            log_info('PDF EXTRACTION succeded using the PyPDF2 fallback', context='resume_parser')
        return result
        
    except Exception as e:
        log_error(e, context='extract_text_from_pdf')
        raise FileParsingError(
            'Failed to extract text from PDF using both pdfplumber and PyPDF2. '
            'The PDF may be corrupted, password-protected, or contain only scanned images. '
            'Please ensure it contains selectable text.'
        ) from e
    
# next lets dicuss on if user upload a docx files
def extract_text_from_docx(file_data: bytes) -> str:
    try:
        doc = Document(io.BytesIO(file_data))
        text_parts = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)
         #if tables exust in the docx so that to be extracted, if we miss this to extract then the imp info missed then the ats score becomes decreases
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        text_parts.append(cell.text)

        text = '\n'.join(text_parts)

        if not text.strip():
            raise FileParsingError(
                'No text could be extracted from the document. '
                'The document may be empty or corrupted.'
            )
        
        try:
            for rel in doc.part.rels.values():
                if 'hyperlink' in rel.reltype.lower():
                    url = rel._target
                    if isinstance(url, str) and url.startswith('http'):
                        text += '\n' + url
        except Exception:
            pass

        log_info(f'Extracted {len(text)} chars from DOCX', context='resume_parser')
        return text.strip()

    except FileParsingError:
        raise   # Re-raise unchanged — don't wrap in another FileParsingError

    except Exception as e:
        log_error(e, context='extract_text_from_docx')
        raise FileParsingError(
            'Failed to extract text from DOCX. '
            'The document may be corrupted or in an unsupported format. '
            'Please try re-saving or converting to PDF.'
        ) from e

def extract_text_from_doc(file_data: bytes) -> str:
    raise FileParsingError(
        'Legacy .doc format is not supported. '
        'Please convert your document to .docx or .pdf and try again. '
        'You can convert using Microsoft Word, Google Docs, or online tools.'
    )


# we defines 3 ways to extract the contents from pdf , docx and doc , if user uploades any one of then how the sysstem will call the which fnction(pdf extractor, docx extractor, doc extactor) basde on the user uploades => how means we define an orhhestrator function based on the user uploades it will calls the preferred function as like below 
#orchestrator
def extract_text(file_data:bytes, file_type:str)->str:
    if file_type=='pdf':
        return extract_text_from_pdf(file_data)
    elif file_type=='docx':
        return extract_text_from_docx(file_data)
    elif file_type=='doc':
        return extract_text_from_doc(file_data)
    else:
        raise FileValidationError(
            f'invalid file type: {file_type}. supported types are: pdf, docx and doc'


        )

#        
def parse_resume_file(file_data: bytes, filename:str)->Tuple[str, dict]:
    log_info(f'parsing file :{filename}', context='parse_Resume_file')

    #phase01:validate file (error will comes during the file validation error)
    try:
        is_valid, error_msg, file_type=validate_file(file_data, filename)
        if not is_valid:
            log_warning(f'valiudation failed for file {filename}', context='parse_resume_file')
            raise FileValidationError(error_msg)
    
    except FileValidationError as e:
        raise 

    except Exception as e:
        log_error(e, context='parse_resume_file_validation')
        raise FileValidationError(
            'Could not validate the uploaded file. Please ensure it is a valid PDF or DOCX.'
        ) from e
    
    #phase02: extraction of file(error will comes during the file extraction error)

    try:
        text = extract_text(file_data, file_type)
        log_info(f'Extracted {len(text)} chars from {filename}', context='parse_resume_file')

    except FileParsingError:
        raise   # Re-raise unchanged

    except Exception as e:
        log_error(e, context='parse_resume_file_extraction')
        raise FileParsingError(
            'An unexpected error occurred while processing the file. '
            'Please try again or contact support if the problem persists.'
        ) from e
     # file information
    metadata = {
        'filename':        filename,
        'file_type':       file_type,
        'file_size_bytes': len(file_data),
        'text_length':     len(text),
        'success':         True,
    }
    return text, metadata
  
