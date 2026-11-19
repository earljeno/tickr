def test_root_unauthenticated(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Login" in response.data or b"Tickr" in response.data


def test_root_redirect_admin(admin_client):
    response = admin_client.get("/")
    assert response.status_code == 302
    assert "/admin/dashboard" in response.headers["Location"]


def test_root_redirect_gia(gia_client):
    response = gia_client.get("/")
    assert response.status_code == 302
    assert "/dashboard" in response.headers["Location"]


def test_admin_login_success(client):
    res = client.post(
        "/auth/login",
        json={"adminId": "admin1", "password": "admin123"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "/admin/dashboard" in data["redirect"]


def test_admin_login_wrong_password(client):
    res = client.post(
        "/auth/login",
        json={"adminId": "admin1", "password": "wrongpassword"},
    )
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False
    assert "Invalid username or password" in data["error"]


def test_gia_login_success(client):
    res = client.post(
        "/auth/login",
        json={"giaId": "2024001"},
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "/dashboard" in data["redirect"]


def test_gia_login_inactive(client):
    res = client.post(
        "/auth/login",
        json={"giaId": "2024002"},
    )
    assert res.status_code == 403
    data = res.get_json()
    assert data["success"] is False
    assert "no longer active" in data["error"]


def test_gia_login_nonexistent(client):
    res = client.post(
        "/auth/login",
        json={"giaId": "9999999"},
    )
    assert res.status_code == 401
    data = res.get_json()
    assert data["success"] is False


def test_logout(gia_client):
    res = gia_client.get("/auth/logout")
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/")
    # Verify redirected to index and logged out
    follow = gia_client.get("/")
    assert follow.status_code == 200
    # Verify protected route is no longer accessible
    dash = gia_client.get("/dashboard")
    assert dash.status_code == 302


def test_admin_logout(admin_client):
    res = admin_client.get("/auth/logout")
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/")
    follow = admin_client.get("/")
    assert follow.status_code == 200
    admin_dash = admin_client.get("/admin/dashboard")
    assert admin_dash.status_code == 302


def test_admin_logout_route_redirect(admin_client):
    res = admin_client.get("/admin/logout")
    assert res.status_code == 302
    assert "/auth/logout" in res.headers["Location"]

