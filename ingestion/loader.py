
# import pandas as pd
# from PyPDF2 import PdfReader

# def load_requirements(file):
#     name = file.name.lower()
#     if name.endswith(".txt"):
#         return file.read().decode()
#     if name.endswith(".pdf"):
#         reader = PdfReader(file)
#         return "\n".join(p.extract_text() for p in reader.pages if p.extract_text())
#     if name.endswith(".csv"):
#         df = pd.read_csv(file)
#         return "\n".join(df.astype(str).agg(" | ".join, axis=1))
#     raise ValueError("Unsupported file")

import pandas as pd
from PyPDF2 import PdfReader

def load_requirements(uploaded_file):
    file_type = uploaded_file.name.split(".")[-1].lower()

    if file_type == "txt":
        return uploaded_file.read().decode("utf-8")

    if file_type == "csv":
        df = pd.read_csv(uploaded_file)
        return "\n".join(
            df.astype(str).apply(lambda row: " | ".join(row), axis=1)
        )

    if file_type == "pdf":
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    raise ValueError("Unsupported file format")
