def test_get_users_unauthenticated(client):
    res = client.get("/api/users-data")
    assert res.status_code == 401


def test_get_users_as_gia_forbidden(gia_client):
    res = gia_client.get("/api/users-data")
    assert res.status_code == 403


def test_get_users_as_admin(admin_client):
    res = admin_client.get("/api/users-data")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "users" in data
    # John Doe should be present
    user_ids = [u["user_id"] for u in data["users"]]
    assert "2024001" in user_ids


def test_add_user_success(admin_client):
    payload = {
        "userId": "2024010",
        "firstName": "Robert",
        "lastName": "Johnson",
        "middleInitial": "M",
        "role": "gia",
        "phoneNumber": "09171234567",
        "laboratory": "204",
    }
    res = admin_client.post("/api/add-user", json=payload)
    assert res.status_code == 200
    assert res.get_json()["success"] is True

    # Check details can be fetched
    get_res = admin_client.get("/api/get-user/2024010")
    assert get_res.status_code == 200
    user_data = get_res.get_json()
    assert user_data["first_name"] == "Robert"
    assert user_data["laboratory"] == "204"


def test_add_user_duplicate(admin_client):
    payload = {
        "userId": "2024001",
        "firstName": "Duplicate",
        "lastName": "User",
        "role": "gia",
    }
    res = admin_client.post("/api/add-user", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.get_json()["error"]


def test_update_user(admin_client):
    payload = {
        "firstName": "Johnny",
        "lastName": "Doe Updated",
        "phoneNumber": "09189876543",
        "laboratory": "Lab 105",
        "role": "gia",
        "status": "active",
    }
    res = admin_client.post("/api/update-user/2024001", json=payload)
    assert res.status_code == 200

    get_res = admin_client.get("/api/get-user/2024001")
    assert get_res.status_code == 200
    data = get_res.get_json()
    assert data["first_name"] == "Johnny"
    assert data["laboratory"] == "Lab 105"


def test_delete_user(admin_client):
    # Create user to delete
    admin_client.post(
        "/api/add-user",
        json={
            "userId": "2024099",
            "firstName": "Temp",
            "lastName": "DeleteMe",
            "role": "gia",
        },
    )

    del_res = admin_client.post("/api/delete-user/2024099")
    assert del_res.status_code == 200

    # Verify not found
    get_res = admin_client.get("/api/get-user/2024099")
    assert get_res.status_code == 404


def test_export_users_csv(admin_client):
    res = admin_client.get("/api/export-users")
    assert res.status_code == 200
    assert res.mimetype == "text/csv"
    assert b"User ID,Last Name,First Name" in res.data
