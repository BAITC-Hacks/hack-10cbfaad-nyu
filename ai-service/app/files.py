import io
from typing import Any
from uuid import UUID

SUPPORTED = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/jpeg": ".jpeg",
}


class AttachmentStore:
    def __init__(self) -> None:
        self._items: dict[UUID, dict[str, Any]] = {}

    def put(self, attachment_id: UUID, file_name: str, mime_type: str, data: bytes) -> dict[str, Any]:
        extracted = extract_file_data(data, mime_type)
        item = {"file_name": file_name, "mime_type": mime_type, "size_bytes": len(data), "extracted": extracted}
        self._items[attachment_id] = item
        return item

    def get(self, attachment_id: UUID) -> dict[str, Any] | None:
        return self._items.get(attachment_id)


def extract_file_data(data: bytes, mime_type: str) -> dict[str, Any]:
    if mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        from openpyxl import load_workbook
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        rows = []
        for sheet in workbook.worksheets:
            for values in sheet.iter_rows(values_only=True):
                cells = [str(value).strip() for value in values if value is not None and str(value).strip()]
                if cells:
                    rows.append(cells)
        return {"kind": "xlsx", "items": rows}
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        from docx import Document
        doc = Document(io.BytesIO(data))
        return {"kind": "docx", "text": "\n".join(p.text for p in doc.paragraphs)}
    if mime_type == "application/pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return {"kind": "pdf", "text": "\n".join(page.extract_text() or "" for page in reader.pages)}
    if mime_type == "image/jpeg":
        return {"kind": "jpeg", "vision_required": True, "text": ""}
    raise ValueError("UNSUPPORTED_FILE_TYPE")


def user_data_context(extracted: dict[str, Any]) -> str:
    """Delimit file content so it can never be treated as system instructions."""
    return "<user_file_data>\n" + repr(extracted) + "\n</user_file_data>"
