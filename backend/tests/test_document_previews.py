from io import BytesIO
from PIL import Image
from reportlab.pdfgen import canvas
from test_workflows import create_customer


def test_image_preview_authorization_and_admin_only_delete(client,db,actors,tmp_path,monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(),'storage_dir',tmp_path)
    owner=actors['test_staff_a']['headers']
    other=actors['test_staff_b']['headers']
    admin=actors['test_admin']['headers']
    customer=create_customer(client,owner)
    image=BytesIO()
    Image.new('RGB',(400,200),'red').save(image,format='JPEG')
    response=client.post('/api/customers/'+customer['id']+'/documents?kind=aadhaar',headers=owner,
                         files={'file':('aadhaar.jpg',image.getvalue(),'image/jpeg')})
    assert response.status_code==201,response.text
    doc=response.json()
    path='/api/documents/'+doc['id']+'/preview'
    assert client.get(path).status_code==401
    assert client.get(path,headers=other).status_code==404
    preview=client.get(path,headers=owner)
    assert preview.status_code==200 and preview.content.startswith(b'\x89PNG')
    assert preview.headers['x-page-count']=='1' and preview.headers['cache-control']=='no-store'
    assert Image.open(BytesIO(preview.content)).size==(400,200)
    assert client.get(path+'?page=2',headers=owner).status_code==404
    assert client.get(path,headers=admin).status_code==200
    assert client.request('DELETE','/api/documents/'+doc['id'],headers=owner,json={'reason':'Requested removal'}).status_code==403
    assert client.request('DELETE','/api/documents/'+doc['id'],headers=admin,json={'reason':'Requested removal'}).status_code==204
    assert client.get(path,headers=owner).status_code==404


def test_multipage_pdf_preview(client,db,actors,tmp_path,monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(),'storage_dir',tmp_path)
    owner=actors['test_staff_a']['headers']
    customer=create_customer(client,owner)
    source=BytesIO()
    pdf=canvas.Canvas(source)
    pdf.drawString(80,700,'First page')
    pdf.showPage()
    pdf.drawString(80,700,'Second page')
    pdf.save()
    response=client.post('/api/customers/'+customer['id']+'/documents?kind=pan',headers=owner,
                         files={'file':('pan.pdf',source.getvalue(),'application/pdf')})
    assert response.status_code==201,response.text
    path='/api/documents/'+response.json()['id']+'/preview'
    first=client.get(path,headers=owner)
    second=client.get(path+'?page=2',headers=owner)
    assert first.status_code==200 and second.status_code==200
    assert first.headers['x-page-count']=='2'
    assert first.content.startswith(b'\x89PNG') and first.content!=second.content
    assert client.get(path+'?page=3',headers=owner).status_code==404
    assert client.get(path+'?page=0',headers=owner).status_code==422
