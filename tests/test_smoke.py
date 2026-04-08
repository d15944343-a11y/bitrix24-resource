from app.models import DatasetAsset, ModelArtifact


def login_as_admin(client):
    return client.post(
        "/login",
        data={"email": "admin@example.com", "password": "admin123"},
    )


def full_client_payload(**overrides):
    payload = {
        "full_name": "Тестовый клиент",
        "customer_code": "CRM-9901",
        "email": "test.client@example.com",
        "phone": "+7 (999) 000-00-00",
        "city": "Москва",
        "status": "Новый",
        "tenure_months": "12",
        "service_count": "3",
        "monthly_charges": "84.5",
        "total_charges": "1014",
        "contract_type": "Month-to-month",
        "payment_method": "Electronic check",
        "internet_service": "Fiber optic",
        "paperless_billing": "on",
        "has_family_plan": "on",
        "has_tech_support": "on",
    }
    payload.update(overrides)
    return payload


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
    response = login_as_admin(client)
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_login_rejects_invalid_email_format(client):
    response = client.post(
        "/login",
        data={"email": "invalid-email", "password": "admin123"},
    )
    assert response.status_code == 200


def test_client_create_rejects_duplicate_email(client):
    login_as_admin(client)
    response = client.post(
        "/clients/create",
        data=full_client_payload(
            full_name="Дубликат клиента",
            customer_code="CRM-9910",
            email="ivan.petrov@example.com",
        ),
    )
    assert response.status_code == 200


def test_ml_lab_is_available_after_login(client):
    login_as_admin(client)
    response = client.get("/ml-lab")
    assert response.status_code == 200


def test_demo_dataset_and_model_are_registered(app):
    with app.app_context():
        assert DatasetAsset.query.count() >= 1
        assert ModelArtifact.query.count() >= 1


def test_recommendations_page_is_available_after_login(client):
    login_as_admin(client)
    response = client.get("/recommendations")
    assert response.status_code == 200
