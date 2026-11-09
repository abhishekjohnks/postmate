import pytest
from sqlalchemy.exc import IntegrityError
from app.models import User
from app.core.security import passwords


def test_single_admin_and_staff_only_management(client, db, actors):
    headers = actors['test_admin']['headers']
    created = client.post('/api/users', headers=headers, json={
        'username': 'test_new_admin', 'full_name': 'Test New Admin', 'password': 'StrongPassword123!', 'role': 'super_admin'})
    assert created.status_code == 422, created.text
    created = client.post('/api/users', headers=headers, json={
        'username': 'test_new_staff', 'full_name': 'Test New Staff', 'password': 'StrongPassword123!'})
    assert created.status_code == 201
    assert created.json()['role'] == 'staff'
    changed = client.patch('/api/users/' + created.json()['id'], headers=headers, json={
        'full_name': 'Test New Staff', 'role': 'staff', 'active': True})
    assert changed.status_code == 200
    assert client.patch('/api/users/' + created.json()['id'], headers=headers, json={
        'full_name': 'Promoted User', 'active': True, 'role': 'super_admin'}).status_code == 422
    response = client.patch('/api/users/' + actors['test_admin']['user'].id, headers=headers, json={
        'full_name': 'Last Admin', 'role': 'staff', 'active': True})
    assert response.status_code == 403
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.add(User(username='second_admin_direct', full_name='Other Admin', role='super_admin',
                        password_hash=passwords.hash('TestPassword123!')))
            db.flush()
