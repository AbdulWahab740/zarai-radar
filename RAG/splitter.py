import os
import re
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader
)

# -------------------------------------------------
# 1️⃣ EXTENSIVE REFERENCE / BIBLIOGRAPHY HEADINGS
# -------------------------------------------------
REFERENCE_HEADINGS = [
    "references",
    "bibliography",
    "works cited",
    "literature cited",
    "cited literature",
    "reference list",
    "references and notes",
    "selected references",
    "references cited",
    "sources",
    "citations",
    "endnotes"
]

# -------------------------------------------------
# 2️⃣ REMOVE ENTIRE REFERENCES SECTION
# -------------------------------------------------
def remove_references_section(text: str) -> str:
    lower_text = text.lower()

    for heading in REFERENCE_HEADINGS:
        # Match heading on new line, with optional numbering
        pattern = rf"\n\s*(\d+\.?\s*)?{heading}\s*\n"
        match = re.search(pattern, lower_text)
        if match:
            return text[:match.start()]

    return text


# -------------------------------------------------
# 3️⃣ REMOVE INLINE CITATIONS (VERY EXTENSIVE)
# -------------------------------------------------
def remove_inline_citations(text: str) -> str:
    patterns = [
        # (Ali et al., 2019)
        r"\([^)]*et al\.,?\s*\d{4}\)",

        # (Ali and Khan, 2019)
        r"\([^)]*(and|&)[^)]*,?\s*\d{4}\)",

        # (Ali, 2019)
        r"\([^)]*,?\s*\d{4}\)",

        # Author et al. (2019)
        r"[A-Z][a-z]+ et al\.\s*\(\d{4}\)",

        # [1], [2,3], [4–6]
        r"\[\s*\d+(?:\s*[,\-–]\s*\d+)*\s*\]",

        # Superscripts ¹²³⁴⁵
        r"[¹²³⁴⁵⁶⁷⁸⁹⁰]+",

        # DOI references
        r"doi:\s*\S+",
        r"https?://doi\.org/\S+",

        # Harvard style inline
        r"\b[A-Z][a-z]+,\s*[A-Z]\.\s*\(\d{4}\)",

        # Year-only citations like (2019)
        r"\(\s*\d{4}\s*\)"
    ]

    for pattern in patterns:
        text = re.sub(pattern, "", text)

    return text


# -------------------------------------------------
# 4️⃣ REMOVE PDF NOISE / FOOTERS / HEADERS
# -------------------------------------------------
def remove_pdf_noise(text: str) -> str:
    noise_patterns = [
        r"Downloaded from .*",
        r"This article.*?license",
        r"©\s*\d{4}.*",
        r"All rights reserved.*",
        r"Page\s+\d+\s*(of\s+\d+)?",
        r"ISSN\s*\d{4}-\d{4}",
        r"e-ISSN\s*\d{4}-\d{4}",
        r"Received:\s*\d+.*",
        r"Accepted:\s*\d+.*",
        r"Published:\s*\d+.*"
    ]

    for pattern in noise_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)

    return text


# -------------------------------------------------
# 5️⃣ FINAL CLEANING PIPELINE
# -------------------------------------------------
def clean_document(text: str) -> str:
    text = remove_references_section(text)
    text = remove_inline_citations(text)
    text = remove_pdf_noise(text)

    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


# -------------------------------------------------
# 6️⃣ LOAD FILES & SPLIT INTO CHUNKS
# -------------------------------------------------
def load_and_split_documents(
    data_dir: str,
    chunk_size: int = 512,
    chunk_overlap: int = 200
) -> List[Document]:

    documents = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators = [
    "\n\n",          # paragraph
    "\n",            # line
    ". ",             # sentence
    "; ",             # clauses
    ", ",             # phrases

]
    )
    filename = data_dir
    if filename.lower().endswith(".pdf"):
            loader = PyPDFLoader(filename)
    elif filename.lower().endswith(".txt"):
            loader = TextLoader(filename)
    elif filename.lower().endswith(".docx"):
            loader = Docx2txtLoader(filename)
    
    loaded_docs = loader.load()

    for doc in loaded_docs:
            cleaned_text = clean_document(doc.page_content)

            if not cleaned_text.strip():
                continue

            chunks = splitter.split_text(cleaned_text)

            for chunk in chunks:
                documents.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            **doc.metadata,
                            "source_file": filename
                        }
                    )
                )

    return documents
