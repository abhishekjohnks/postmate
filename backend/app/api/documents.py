from io import BytesIO
from pathlib import Path
from uuid import uuid4
from threading import Lock
from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Query, Response, UploadFile
from PIL import Image
import pypdfium2 as pdfium
from sqlalchemy import select
from app.api.helpers import data
from app.core.config import get_settings
from app.core.security import Actor, Admin, DB, audit
from app.models import CustomerDocument
from app.repositories import customer_for
from app.schemas import Reason

router = APIRouter(tags=["Private documents"])
LIMIT = 5 * 1024 * 1024
_pdf_lock = Lock()


@router.get("/customers/{customer_id}/documents")
def documents(customer_id: str, db: DB, actor: Actor):
    customer_for(db, actor, customer_id)
    return [data(row, {"storage_key"}) for row in db.scalars(select(CustomerDocument).where(CustomerDocument.customer_id == customer_id))]


@router.post("/customers/{customer_id}/documents", status_code=201)
async def upload(customer_id: str, file: UploadFile, db: DB, actor: Actor, kind: str = Query(pattern="^(aadhaar|pan|other)$")):
    customer_for(db, actor, customer_id)
    content = await file.read(LIMIT + 1)
    await file.close()
    if not content or len(content) > LIMIT:
        raise HTTPException(422, "Documents must be between 1 byte and 5 MB")
    if content.startswith(b"%PDF-") and b"%%EOF" in content[-1024:]:
        content_type = "application/pdf"
    else:
        try:
            with Image.open(BytesIO(content)) as image:
                if image.format not in {"PNG", "JPEG"} or image.width * image.height > 25_000_000:
                    raise ValueError()
                content_type = "image/png" if image.format == "PNG" else "image/jpeg"
                image.verify()
        except Exception:
            raise HTTPException(422, "Upload a valid PDF, PNG or JPEG")
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    key = uuid4().hex + ".enc"
    path = settings.storage_dir / key
    path.write_bytes(Fernet(settings.encryption_key.encode()).encrypt(content))
    row = CustomerDocument(customer_id=customer_id, kind=kind, storage_key=key,
                            content_type=content_type, size=len(content), uploaded_by=actor.id)
    try:
        db.add(row)
        db.flush()
        audit(db, actor, "document.uploaded", "customer_documents", row.id)
        # Commit metadata before returning; remove the blob if persistence fails.
        db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return data(row, {"storage_key"})


@router.get("/documents/{document_id}")
def download(document_id: str, db: DB, actor: Actor):
    row = db.get(CustomerDocument, document_id)
    if not row:
        raise HTTPException(404, "Document not found")
    customer_for(db, actor, row.customer_id)
    settings = get_settings()
    path = settings.storage_dir / row.storage_key
    if not path.is_file():
        raise HTTPException(404, "Document content is unavailable")
    content = Fernet(settings.encryption_key.encode()).decrypt(path.read_bytes())
    audit(db, actor, "document.downloaded", "customer_documents", row.id)
    extension = {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg"}[row.content_type]
    return Response(content, media_type=row.content_type, headers={
        "Content-Disposition": f'attachment; filename="{row.kind}-{row.id}.{extension}"',
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: str, payload: Reason, db: DB, actor: Admin):
    row = db.get(CustomerDocument, document_id)
    if not row:
        raise HTTPException(404, "Document not found")
    customer_for(db, actor, row.customer_id)
    path = get_settings().storage_dir / row.storage_key
    audit(db, actor, "document.deleted", "customer_documents", row.id, {"reason": payload.reason})
    db.delete(row)
    db.commit()
    path.unlink(missing_ok=True)


@router.get("/documents/{document_id}/preview")
def preview_document(document_id: str, db: DB, actor: Actor, page: int = Query(1, ge=1)):
    row = db.get(CustomerDocument, document_id)
    if not row:
        raise HTTPException(404, "Document not found")
    customer_for(db, actor, row.customer_id)
    settings = get_settings()
    path = settings.storage_dir / row.storage_key
    if not path.is_file():
        raise HTTPException(404, "Document content is unavailable")
    content = Fernet(settings.encryption_key.encode()).decrypt(path.read_bytes())
    output = BytesIO()
    page_count = 1
    try:
        if row.content_type == "application/pdf":
            # PDFium is serialized across request threads. Only rasterized pages reach the browser.
            with _pdf_lock, pdfium.PdfDocument(content) as document:
                page_count = len(document)
                if page > page_count:
                    raise HTTPException(404, "Document page not found")
                pdf_page = document[page - 1]
                try:
                    width, height = pdf_page.get_size()
                    scale = min(2, 2200 / max(width, height, 1))
                    bitmap = pdf_page.render(scale=scale)
                    try:
                        bitmap.to_pil().save(output, format="PNG")
                    finally:
                        bitmap.close()
                finally:
                    pdf_page.close()
        else:
            if page != 1:
                raise HTTPException(404, "Document page not found")
            with Image.open(BytesIO(content)) as picture:
                picture.thumbnail((2200, 2200))
                picture.convert("RGB").save(output, format="PNG")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, "This document cannot be previewed. Download it to view the original file.")
    audit(db, actor, "document.previewed", "customer_documents", row.id, {"page": page})
    return Response(output.getvalue(), media_type="image/png", headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-Page-Count": str(page_count)})
