"""Render a synthetic design sample without inserting any database records."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import pypdfium2 as pdfium
from app.services.receipts import render_receipt
from test_receipts import sample_receipt

destination = Path("storage/receipt-preview")
destination.mkdir(parents=True, exist_ok=True)
content = render_receipt(sample_receipt())
(destination / "PostMate-receipt-preview.pdf").write_bytes(content)
with pdfium.PdfDocument(content) as document:
    page = document[0]
    bitmap = page.render(scale=1.6)
    bitmap.to_pil().save(destination / "PostMate-receipt-preview.png")
    bitmap.close()
    page.close()
    print("Preview saved; PDF pages:", len(document))
