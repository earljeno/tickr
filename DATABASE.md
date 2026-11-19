# Database Documentation

## Schema Overview

Tickr uses SQLAlchemy ORM supporting both SQLite and MySQL databases.

```mermaid
erDiagram
    USER ||--o{ ATTENDANCE : "logs attendance"
    USER ||--o{ SCHEDULE : "assigned"
    USER ||--o{ LOGS : "generates"
    USER ||--o{ ATTENDANCE_INCONSISTENCY : "flags"

    USER {
        int id PK
        string user_id UK
        string first_name
        string last_name
        string middle_name
        string phone_number
        string laboratory
        string password
        string role
        string status
    }

    ATTENDANCE {
        int id PK
        string user_id FK
        date date
        time clock_in
        time clock_out
        boolean is_manual
    }

    SCHEDULE {
        int id PK
        string user_id FK
        string day
        time start_time
        time end_time
        boolean is_split_shift
        time split_start_time
        time split_end_time
    }

    GLOBAL_SETTINGS {
        int id PK
        string unit_head
        boolean enable_strict_schedule
        date strict_duration
        boolean allow_early_out
        boolean allow_overtime
        time default_start
        time default_end
        int allowed_early_in_mins
    }

    LOGS {
        int id PK
        string user_id FK
        string action
        datetime timestamp
        text details
        string client_ip
    }

    ATTENDANCE_INCONSISTENCY {
        int id PK
        string user_id FK
        date date
        string issue_type
        text details
        datetime created_at
    }
```

---

## Constraints & Indexes

1. **User Table:**
   - Primary key on `id`.
   - Unique, indexed constraint on `user_id`.
2. **Attendance Table:**
   - Composite index `idx_attendance_user_date` on `(user_id, date)` for rapid date range lookups.
   - Foreign key to `user.user_id` with `ON DELETE CASCADE`.
3. **Schedule Table:**
   - Unique constraint `unique_schedule_per_user_day` on `(user_id, day)` preventing duplicate shifts per block.
   - Day values: `mw`, `tth`, `fri`, `sat`.
4. **Logs Table:**
   - Foreign key to `user.user_id` with `ON DELETE SET NULL`.
   - Index on `timestamp` for descending audit log pagination.
5. **Alembic Migrations:**
   - Linear migration chain managed through Flask-Migrate:
     - `bfbe947c2750`: Initial schema.
     - `c7ca0d8dc6dd`: Added phone number and laboratory to user.
