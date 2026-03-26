def test_public_pages_are_available(client):
    for path in ["/", "/about", "/contacts"]:
        response = client.get(path)
        assert response.status_code == 200


def test_missing_page_returns_404(client):
    response = client.get("/page-that-does-not-exist")
    assert response.status_code == 404


def test_protected_dashboard_redirects_guest_to_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_with_demo_user_redirects_to_dashboard(client):
    response = client.post(
        "/login",
        data={
            "email": "admin@example.com",
            "password": "admin123",
        },
    )
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_login_rejects_invalid_email_format(client):
    response = client.post(
        "/login",
        data={
            "email": "invalid-email",
            "password": "admin123",
        },
    )
    assert response.status_code == 200


def test_client_create_rejects_duplicate_email(client):
    client.post(
        "/login",
        data={
            "email": "admin@example.com",
            "password": "admin123",
        },
    )
    response = client.post(
        "/clients/create",
        data={
            "full_name": "Дубликат клиента",
            "email": "ivan.petrov@example.com",
            "phone": "+7 (900) 000-00-00",
            "city": "Москва",
            "status": "Новый",
        },
    )
    assert response.status_code == 200
