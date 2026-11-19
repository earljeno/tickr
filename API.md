# API Reference

All API routes are served under the `/api` prefix and return JSON unless specified otherwise (e.g. file exports).

## Authentication & Headers
- Stateful session cookies (`session`).
- Unauthenticated requests receive `401 Unauthorized`.
- Forbidden requests (insufficient role privileges) receive `403 Forbidden`.

---

## User Management Endpoints

### 1. `GET /api/users-data`
- **Role Required:** `admin`, `superadmin`
- **Query Params:**
  - `page` (int, default 1)
  - `per_page` (int, default 10, max 100)
  - `search` (str, filter by name, ID, phone, laboratory)
  - `role` (str, `admin` | `gia`)
  - `status` (str, `active` | `inactive`)
- **Response:**
  ```json
  {
    "success": true,
    "users": [...],
    "total": 25,
    "page": 1,
    "per_page": 10
  }
  ```

### 2. `POST /api/add-user`
- **Role Required:** `admin`, `superadmin`
- **Payload:**
  ```json
  {
    "userId": "2024015",
    "firstName": "Juan",
    "lastName": "Dela Cruz",
    "middleInitial": "D",
    "role": "gia",
    "phoneNumber": "09171234567",
    "laboratory": "204"
  }
  ```
- **Response:** `200 OK` `{ "success": true }`

### 3. `GET /api/get-user/<user_id>`
- **Role Required:** `admin`, `superadmin`
- **Response:** `200 OK` with user details object.

### 4. `POST /api/update-user/<user_id>`
- **Role Required:** `admin`, `superadmin`
- **Payload:** Updated user attributes.

### 5. `POST /api/delete-user/<user_id>`
- **Role Required:** `admin`, `superadmin`
- **Response:** `200 OK` `{ "success": true, "message": "User deleted successfully!" }`

### 6. `GET /api/export-users`
- **Role Required:** `admin`, `superadmin`
- **Response:** CSV file attachment (`GIA List MM-DD-YYYY.csv`).

---

## Attendance & Clock-In Endpoints

### 1. `GET /api/status?user_id=<user_id>`
- **Role Required:** Authenticated user (self) or admin
- **Response:**
  ```json
  {
    "clocked_in": true,
    "clocked_out": false,
    "is_grace": false
  }
  ```

### 2. `POST /api/clock-in`
- **Role Required:** Authenticated user (self) + Whitelisted IP
- **Payload:** `{ "user_id": "2024001" }`
- **Response:**
  ```json
  {
    "success": true,
    "message": "Clock-in successful!",
    "data": {
      "user_id": "2024001",
      "time_record": "08:02 AM",
      "date": "2026-11-19",
      "shift": "first"
    }
  }
  ```

### 3. `POST /api/clock-out`
- **Role Required:** Authenticated user (self) + Whitelisted IP
- **Payload:** `{ "user_id": "2024001" }`
- **Response:**
  ```json
  {
    "success": true,
    "message": "Clock-out successful!",
    "data": {
      "user_id": "2024001",
      "time_record": "05:01 PM",
      "date": "2026-11-19",
      "shift": "first"
    }
  }
  ```

### 4. `GET /api/gia-data?user_id=<id>&month=YYYY-MM`
- **Role Required:** Authenticated user (self) or admin
- **Response:** Historical attendance logs and monthly hours summary.

---

## Schedule Endpoints

### 1. `GET /api/get-schedules`
- **Role Required:** `admin`, `superadmin`
- **Response:** Matrix of all active GIA block schedules.

### 2. `GET /api/get-schedule/<user_id>`
- **Role Required:** Self or admin
- **Response:** List of daily blocks for the requested user.

### 3. `POST /api/update-schedule/<user_id>`
- **Role Required:** `admin`, `superadmin`
- **Payload:** Array of block objects (`day`, `start_time`, `end_time`, `is_split_shift`, etc.).

### 4. `POST /api/purge-schedules`
- **Role Required:** `admin`, `superadmin`
- **Response:** `200 OK` with confirmation.

---

## Settings & Profile Endpoints

- `GET /api/get-settings`: Retrieve global system settings.
- `POST /api/update-settings`: Update unit head, strict mode, and hours allowances.
- `POST /api/update-profile`: Update current user's name fields.
- `POST /api/change-password`: Update current user's password with old password verification.
