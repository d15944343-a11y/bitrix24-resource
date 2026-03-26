def test_public_pages_are_available(client):
    for path in ["/", "/about", "/contacts"]:
        response = client.get(path)
        assert response.status_code == 200


def test_missing_page_returns_404(client):
    response = client.get("/page-that-does-not-exist")
    assert response.status_code == 404
