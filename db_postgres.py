"""
╔══════════════════════════════════════════════════════════════╗
║         MedRemind — Production Database Layer                ║
║                                                              ║
║  SCHEMA DESIGN (Normalized, FK-linked):                      ║
║                                                              ║
║  users                                                       ║
║    └── patient_records  (FK: user_id → users.id)            ║
║          └── confirmed_medicines  (FK: patient_id → id)     ║
║          └── prescription_schedules (FK: patient_id → id)   ║
║                                                              ║
║  Rule:                                                       ║
║    patient_records  → personal info ONLY                     ║
║    confirmed_medicines → medicines ONLY (separate table)     ║
║    ON DELETE CASCADE → child rows auto-delete with parent    ║
╚══════════════════════════════════════════════════════════════╝
"""

import hashlib
import json
from datetime import date, datetime

import psycopg2
import psycopg2.extras

from config import DB_CONFIG
from medication_utils import (
    compute_end_date,
    is_medicine_active,
    parse_duration_days,
    parse_start_date,
)

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()


def _timing_matches_field(timing_field: str, label: str) -> bool:
    parts = [t.strip() for t in (timing_field or "").split(",") if t.strip()]
    return label in parts


def _backfill_duration_days(cur) -> None:
    """Parse duration text into duration_days for existing rows."""
    cur.execute("""
        SELECT id, duration FROM confirmed_medicines
        WHERE duration_days IS NULL AND duration IS NOT NULL
    """)
    for row_id, duration_text in cur.fetchall():
        days = parse_duration_days(duration_text)
        if days is not None:
            cur.execute(
                "UPDATE confirmed_medicines SET duration_days = %s WHERE id = %s",
                (days, row_id),
            )


# ══════════════════════════════════════════
#  INIT — CREATE ALL TABLES
# ══════════════════════════════════════════
def init_db():
    conn = get_connection()
    cur  = conn.cursor()

    # ── Table 1: users ──────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            SERIAL PRIMARY KEY,
            full_name     TEXT        NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT        NOT NULL,
            role          TEXT        NOT NULL DEFAULT 'user',
            created_at    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ── Table 2: patient_records (parent) ───────────────────────
    # No medicines column — clean separation
    cur.execute("""
        CREATE TABLE IF NOT EXISTS patient_records (
            id                SERIAL      PRIMARY KEY,
            user_id           INTEGER     REFERENCES users(id) ON DELETE SET NULL,
            full_name         TEXT        NOT NULL,
            age               TEXT,
            gender            TEXT,
            phone             TEXT,
            email             TEXT        UNIQUE,
            disease           TEXT,
            doctor_notes      TEXT,
            prescription_date TEXT,
            added_by          TEXT        DEFAULT 'admin',
            added_by_email    TEXT,
            created_at        TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        ALTER TABLE patient_records
        ADD COLUMN IF NOT EXISTS added_by_email TEXT;
    """)
    # Backfill: link old rows via user_id → users.email
    cur.execute("""
        UPDATE patient_records pr
        SET added_by_email = u.email
        FROM users u
        WHERE pr.user_id = u.id
          AND (pr.added_by_email IS NULL OR pr.added_by_email = '');
    """)

    # ── Table 3: confirmed_medicines (child) ────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS confirmed_medicines (
            id            SERIAL    PRIMARY KEY,
            patient_id    INTEGER   NOT NULL
                            REFERENCES patient_records(id)
                            ON DELETE CASCADE,
            patient_email TEXT      NOT NULL,
            patient_name  TEXT      NOT NULL,
            medicine_name TEXT      NOT NULL,
            dose          TEXT,
            uses          TEXT,
            duration      TEXT,
            timing        TEXT,
            start_date    DATE,
            duration_days INTEGER,
            added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        ALTER TABLE confirmed_medicines
        ADD COLUMN IF NOT EXISTS start_date DATE;
    """)
    cur.execute("""
        ALTER TABLE confirmed_medicines
        ADD COLUMN IF NOT EXISTS duration_days INTEGER;
    """)
    cur.execute("""
        UPDATE confirmed_medicines
        SET start_date = COALESCE(start_date, added_at::date)
        WHERE start_date IS NULL AND added_at IS NOT NULL;
    """)
    _backfill_duration_days(cur)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_confirmed_medicines_patient_id
        ON confirmed_medicines(patient_id);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_confirmed_medicines_active
        ON confirmed_medicines (start_date, duration_days);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_confirmed_medicines_email
        ON confirmed_medicines(patient_email);
    """)

    # ── Table 4: prescription_schedules ────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prescription_schedules (
            id             SERIAL    PRIMARY KEY,
            patient_id     INTEGER   REFERENCES patient_records(id) ON DELETE CASCADE,
            patient_email  TEXT      NOT NULL,
            patient_name   TEXT      NOT NULL,
            schedule_json  TEXT      NOT NULL,
            extracted_text TEXT,
            created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ── Table 5: email_logs ────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id            SERIAL    PRIMARY KEY,
            patient_email TEXT      NOT NULL,
            patient_name  TEXT      NOT NULL,
            timing        TEXT      NOT NULL,
            status        TEXT      NOT NULL,
            doctor_email  TEXT,
            sent_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cur.execute("""
        ALTER TABLE email_logs
        ADD COLUMN IF NOT EXISTS doctor_email TEXT;
    """)

    # Default admin seed
    cur.execute("SELECT id FROM users WHERE email = %s", ("admin@medremind.com",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash, role) "
            "VALUES (%s,%s,%s,%s)",
            ("Admin", "admin@medremind.com", hash_password("Admin@123"), "admin")
        )

    conn.commit()
    cur.close()
    conn.close()


# ══════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════
def register_user(full_name, email, password, role="user"):
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT id FROM users WHERE email=%s", (email.lower().strip(),))
    if cur.fetchone():
        cur.close(); conn.close()
        return {"success": False, "message": "Email already registered!"}
    try:
        cur.execute(
            "INSERT INTO users (full_name,email,password_hash,role) "
            "VALUES (%s,%s,%s,%s) RETURNING id",
            (full_name.strip(), email.lower().strip(), hash_password(password), role)
        )
        user_id = cur.fetchone()["id"]
        conn.commit(); cur.close(); conn.close()
        if role == "user":
            _auto_add_patient(user_id, full_name.strip(), email.lower().strip())
        return {"success": True, "message": "Account created!"}
    except Exception as e:
        conn.rollback(); cur.close(); conn.close()
        return {"success": False, "message": str(e)}


def _auto_add_patient(user_id, full_name, email):
    """Auto-create patient_record when user signs up."""
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("SELECT id FROM patient_records WHERE email=%s", (email,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO patient_records (user_id,full_name,email,added_by) "
                "VALUES (%s,%s,%s,%s)",
                (user_id, full_name, email, "auto")
            )
            conn.commit()
    except Exception:
        conn.rollback()
    finally:
        cur.close(); conn.close()


def login_user(email, password):
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id,full_name,email,role FROM users "
        "WHERE email=%s AND password_hash=%s",
        (email.lower().strip(), hash_password(password))
    )
    user = cur.fetchone()
    cur.close(); conn.close()
    if user:
        return {"success": True, "user": dict(user)}
    return {"success": False, "message": "Wrong email or password!"}


def get_all_users(role="user"):
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id,full_name,email,created_at FROM users WHERE role=%s", (role,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


# ══════════════════════════════════════════
#  PATIENT RECORDS  (parent table)

#  user_id        = FK → users.id (same doctor)
# ══════════════════════════════════════════
def get_user_email_by_id(user_id: int | None) -> str | None:
    """Logged-in doctor ka email — users table se."""
    if not user_id:
        return None
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def add_patient(full_name, age, gender, phone, email,
                disease, doctor_notes, prescription_date,
                added_by="admin", user_id=None, added_by_email=None):
    """
    Save patient personal info into patient_records.
    Returns patient_id (PK) which MUST be used to save medicines.
    NO medicines stored here — use save_confirmed_medicines().
    """
    conn        = get_connection()
    cur         = conn.cursor()
    email_clean = email.lower().strip() if email and email.strip() else None
    creator_email = (added_by_email or "").strip().lower() or get_user_email_by_id(user_id)

    try:
        existing_id = None
        if email_clean:
            cur.execute(
                "SELECT id, user_id FROM patient_records WHERE email=%s",
                (email_clean,),
            )
            row = cur.fetchone()
            if row:
                row_id, row_user_id = row[0], row[1]
                if user_id is None:
                    if row_user_id is None:
                        existing_id = row_id
                elif row_user_id is None or row_user_id == user_id:
                    existing_id = row_id
                else:
                    cur.close()
                    conn.close()
                    return {
                        "success": False,
                        "message": (
                            f"This patient email is already registered under another "
                            f"doctor (patient id {row_id}). Use a different email or "
                            f"open that patient from All Patients."
                        ),
                    }

        if existing_id:
            cur.execute("""
                UPDATE patient_records SET
                    user_id=COALESCE(%s, user_id),
                    full_name=%s, age=%s, gender=%s, phone=%s,
                    disease=%s, doctor_notes=%s,
                    prescription_date=%s, added_by=%s,
                    added_by_email=COALESCE(%s, added_by_email)
                WHERE id=%s
            """, (user_id, full_name, age, gender, phone,
                disease, doctor_notes, prescription_date,
                added_by, creator_email, existing_id))
            patient_id = existing_id
        else:
            cur.execute("""
                INSERT INTO patient_records
                    (user_id, full_name, age, gender, phone, email,
                    disease, doctor_notes, prescription_date, added_by,
                    added_by_email)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (user_id, full_name, age, gender, phone, email_clean,
                disease, doctor_notes, prescription_date, added_by,
                creator_email))
            patient_id = cur.fetchone()[0]

        conn.commit()
        cur.close(); conn.close()
        return {"success": True, "patient_id": patient_id}

    except Exception as e:
        conn.rollback(); cur.close(); conn.close()
        return {"success": False, "message": str(e)}


def update_patient(patient_id: int, full_name, age, gender, phone, email,
                disease, doctor_notes, prescription_date, added_by="admin",
                user_id=None, added_by_email=None):
    """
    Update an existing patient record by patient_id.
    When user_id is set, only rows owned by that user can be updated.
    Returns same dict format as add_patient.
    """
    conn = get_connection()
    cur  = conn.cursor()
    email_clean = email.lower().strip() if email and email.strip() else None
    creator_email = (added_by_email or "").strip().lower() or get_user_email_by_id(user_id)
    try:
        if user_id is not None:
            cur.execute("""
                UPDATE patient_records SET
                    full_name=%s, age=%s, gender=%s, phone=%s, email=%s,
                    disease=%s, doctor_notes=%s, prescription_date=%s, added_by=%s,
                    added_by_email=COALESCE(%s, added_by_email)
                WHERE id=%s AND user_id=%s
            """, (full_name, age, gender, phone, email_clean,
                disease, doctor_notes, prescription_date, added_by,
                creator_email, patient_id, user_id))
        else:
            cur.execute("""
                UPDATE patient_records SET
                    full_name=%s, age=%s, gender=%s, phone=%s, email=%s,
                    disease=%s, doctor_notes=%s, prescription_date=%s, added_by=%s,
                    added_by_email=COALESCE(%s, added_by_email)
                WHERE id=%s
            """, (full_name, age, gender, phone, email_clean,
                disease, doctor_notes, prescription_date, added_by,
                creator_email, patient_id))
        if cur.rowcount == 0:
            conn.rollback()
            cur.close(); conn.close()
            return {"success": False, "message": "Patient not found or access denied."}
        conn.commit()
        cur.close(); conn.close()
        return {"success": True, "patient_id": patient_id}
    except Exception as e:
        conn.rollback(); cur.close(); conn.close()
        return {"success": False, "message": str(e)}


def get_all_patients(user_id=None):
    """
    Fetch patient records. When user_id is set, return only that user's patients.

    Returns added_by_email / owner_email = doctor login email jisne patient add kiya.
    patient email column = patient ka apna email (alag).
    """
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if user_id is not None:
        cur.execute("""
            SELECT pr.*,
                   u.email AS owner_email,
                   u.full_name AS owner_name,
                   COALESCE(NULLIF(TRIM(pr.added_by_email), ''), u.email) AS creator_email
            FROM patient_records pr
            LEFT JOIN users u ON pr.user_id = u.id
            WHERE pr.user_id = %s
            ORDER BY pr.created_at DESC
        """, (user_id,))
    else:
        cur.execute("""
            SELECT pr.*,
                   u.email AS owner_email,
                   u.full_name AS owner_name,
                   COALESCE(NULLIF(TRIM(pr.added_by_email), ''), u.email) AS creator_email
            FROM patient_records pr
            LEFT JOIN users u ON pr.user_id = u.id
            ORDER BY pr.created_at DESC
        """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def get_patient_by_email(email):
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT pr.*,
               u.email AS owner_email,
               u.full_name AS owner_name,
               COALESCE(NULLIF(TRIM(pr.added_by_email), ''), u.email) AS creator_email
        FROM patient_records pr
        LEFT JOIN users u ON pr.user_id = u.id
        WHERE pr.email = %s
    """, (email.lower().strip(),))
    row = cur.fetchone()
    cur.close(); conn.close()
    return dict(row) if row else None


def get_patient_id_by_email(email) -> int | None:
    """Quick helper — returns just the patient_id integer."""
    p = get_patient_by_email(email)
    return p["id"] if p else None


def get_patients_by_user(user_id: int) -> list:
    """Return all patient_records that belong to a given user_id."""
    return get_all_patients(user_id=user_id)


def delete_patient(patient_id, user_id=None):
    """
    Delete patient. CASCADE auto-deletes all confirmed_medicines
    for this patient. When user_id is set, only owned rows are deleted.
    """
    conn = get_connection()
    cur  = conn.cursor()
    if user_id is not None:
        cur.execute(
            "DELETE FROM patient_records WHERE id=%s AND user_id=%s",
            (patient_id, user_id),
        )
    else:
        cur.execute("DELETE FROM patient_records WHERE id=%s", (patient_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    cur.close(); conn.close()
    return {"success": deleted}


# ══════════════════════════════════════════
#  CONFIRMED MEDICINES  (child table)
# ══════════════════════════════════════════
def save_confirmed_medicines(patient_id: int,
                            patient_email: str,
                            patient_name: str,
                            medicines_list: list,
                            course_start_date=None) -> dict:
    """
    Bulk insert medicines into confirmed_medicines table.

    Args:
        patient_id    : FK → patient_records.id  (REQUIRED — must be passed!)
        patient_email : for fast email-based lookups
        patient_name  : denormalized for display
        medicines_list: list of dicts from UI
    """
    if not patient_id:
        return {"success": False, "message": "patient_id is required (FK)"}

    conn = get_connection()
    cur  = conn.cursor()

    try:
        # Delete existing medicines for this patient (clean re-save)
        cur.execute(
            "DELETE FROM confirmed_medicines WHERE patient_id = %s",
            (patient_id,)
        )

        default_start = parse_start_date(course_start_date) or date.today()

        insert_query = """
            INSERT INTO confirmed_medicines
                (patient_id, patient_email, patient_name,
                medicine_name, dose, uses, duration, timing,
                start_date, duration_days)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        rows_to_insert = []
        for med in medicines_list:
            times = med.get("times", [])
            if isinstance(times, list):
                timing_str = ", ".join(t.strip() for t in times if t)
            else:
                timing_str = str(times)

            duration_text = med.get("duration", "") or ""
            duration_days = parse_duration_days(duration_text)
            med_start = parse_start_date(med.get("start_date")) or default_start

            rows_to_insert.append((
                patient_id,
                patient_email.lower().strip(),
                patient_name,
                med.get("name", "").strip(),
                med.get("dose", ""),
                med.get("uses") or med.get("instructions", ""),
                duration_text,
                timing_str,
                med_start,
                duration_days,
            ))

        cur.executemany(insert_query, rows_to_insert)
        conn.commit()
        cur.close(); conn.close()
        return {"success": True, "inserted": len(rows_to_insert)}

    except psycopg2.errors.ForeignKeyViolation:
        conn.rollback(); cur.close(); conn.close()
        return {
            "success": False,
            "message": f"patient_id={patient_id} does not exist in patient_records!"
        }
    except Exception as e:
        conn.rollback(); cur.close(); conn.close()
        return {"success": False, "message": str(e)}


def get_confirmed_medicines(patient_email: str, active_only: bool = False) -> list:
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM confirmed_medicines "
        "WHERE patient_email=%s ORDER BY added_at ASC",
        (patient_email.lower().strip(),)
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    result = []
    for r in rows:
        row = dict(r)
        t = row.get("timing", "") or ""
        row["timing_list"] = [x.strip() for x in t.split(",") if x.strip()]
        if active_only and not is_medicine_active(
            row.get("start_date"),
            row.get("duration_days"),
            row.get("duration"),
        ):
            continue
        result.append(row)
    return result


def get_active_reminder_patients(timing: str, as_of_date: date | None = None) -> list:
    """
    Patients with at least one active medicine for `timing` (cron / scheduler).

    Only includes medicines where today <= end_date (start_date + duration_days).
    """
    ref = as_of_date or date.today()
    label = (timing or "").strip().title()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            patient_email,
            patient_name,
            medicine_name,
            dose,
            duration,
            timing,
            start_date,
            duration_days
        FROM confirmed_medicines
        ORDER BY patient_email, medicine_name
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    patients: dict[str, dict] = {}
    skipped_expired = 0
    skipped_no_duration = 0

    for row in rows:
        if not _timing_matches_field(row["timing"], label):
            continue

        email = (row["patient_email"] or "").strip().lower()
        if "@" not in email or email.endswith("@medremind.local"):
            continue

        start = row.get("start_date")
        if isinstance(start, datetime):
            start = start.date()

        if not is_medicine_active(start, row.get("duration_days"), row.get("duration"), reference_date=ref):
            if start and row.get("duration_days"):
                skipped_expired += 1
            else:
                skipped_no_duration += 1
            continue

        if email not in patients:
            patients[email] = {
                "name": row["patient_name"],
                "email": email,
                "medicines": [],
            }

        end = None
        if start and row.get("duration_days"):
            from medication_utils import compute_end_date
            end = compute_end_date(start, row["duration_days"])

        patients[email]["medicines"].append({
            "name": row["medicine_name"],
            "dose": row["dose"] or "-",
            "duration": row["duration"] or "-",
            "start_date": start.isoformat() if start else None,
            "end_date": end.isoformat() if end else None,
        })

    return list(patients.values())


def get_confirmed_medicines_by_id(patient_id: int) -> list:
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM confirmed_medicines "
        "WHERE patient_id=%s ORDER BY added_at ASC",
        (patient_id,)
    )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    for r in rows:
        t = r.get("timing", "") or ""
        r["timing_list"] = [x.strip() for x in t.split(",") if x.strip()]
    return rows


def get_all_confirmed_medicines() -> list:
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            cm.id,
            cm.patient_id,
            cm.patient_email,
            cm.patient_name,
            cm.medicine_name,
            cm.dose,
            cm.uses,
            cm.duration,
            cm.timing,
            cm.added_at,
            pr.age,
            pr.gender,
            pr.disease,
            pr.prescription_date,
            pr.phone
        FROM confirmed_medicines cm
        LEFT JOIN patient_records pr
            ON cm.patient_id = pr.id
        ORDER BY cm.added_at DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    for r in rows:
        t = r.get("timing", "") or ""
        r["timing_list"] = [x.strip() for x in t.split(",") if x.strip()]
    return rows


def delete_confirmed_medicine(medicine_id: int) -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM confirmed_medicines WHERE id=%s", (medicine_id,))
    conn.commit()
    cur.close(); conn.close()
    return {"success": True}


# ══════════════════════════════════════════
#  PRESCRIPTION SCHEDULES
# ══════════════════════════════════════════
def save_prescription_schedule(patient_email, patient_name,
                                schedule_list, extracted_text="",
                                patient_id=None):
    conn = get_connection()
    cur  = conn.cursor()
    email_clean = patient_email.lower().strip() if patient_email else ""
    try:
        if patient_id:
            cur.execute(
                "DELETE FROM prescription_schedules WHERE patient_id=%s",
                (patient_id,),
            )
        elif email_clean:
            cur.execute(
                "DELETE FROM prescription_schedules WHERE LOWER(patient_email)=%s",
                (email_clean,),
            )
        cur.execute("""
            INSERT INTO prescription_schedules
                (patient_id, patient_email, patient_name,
                schedule_json, extracted_text)
            VALUES (%s,%s,%s,%s,%s)
        """, (patient_id, patient_email, patient_name,
            json.dumps(schedule_list), extracted_text))
        conn.commit()
        cur.close(); conn.close()
        return {"success": True}
    except Exception as e:
        conn.rollback(); cur.close(); conn.close()
        return {"success": False, "message": str(e)}


def _latest_schedule_per_patient(rows: list) -> list:
    """Keep only the newest schedule row per patient (avoids duplicate UI entries)."""
    latest = {}
    for r in rows:
        key = r.get("patient_id") or (r.get("patient_email") or "").lower()
        prev = latest.get(key)
        if not prev:
            latest[key] = r
            continue
        ca, pa = r.get("created_at"), prev.get("created_at")
        if ca and pa and ca > pa:
            latest[key] = r
        elif ca and not pa:
            latest[key] = r
    return sorted(latest.values(), key=lambda x: x.get("created_at") or "", reverse=True)


def get_all_schedules(user_id=None):
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if user_id is not None:
        cur.execute("""
            SELECT ps.*
            FROM prescription_schedules ps
            WHERE ps.patient_id IN (
                SELECT id FROM patient_records WHERE user_id = %s
            )
            OR (
                ps.patient_id IS NULL
                AND LOWER(ps.patient_email) IN (
                    SELECT LOWER(email) FROM patient_records
                    WHERE user_id = %s AND email IS NOT NULL
                )
            )
            ORDER BY ps.created_at DESC
        """, (user_id, user_id))
    else:
        cur.execute(
            "SELECT * FROM prescription_schedules ORDER BY created_at DESC"
        )
    rows = cur.fetchall()
    cur.close(); conn.close()
    result = []
    for row in rows:
        r = dict(row)
        try:    r["schedule"] = json.loads(r["schedule_json"])
        except: r["schedule"] = []
        result.append(r)
    return _latest_schedule_per_patient(result)


def get_schedule_by_email(email):
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT * FROM prescription_schedules "
        "WHERE patient_email=%s ORDER BY created_at DESC",
        (email.lower().strip(),)
    )
    rows = cur.fetchall()
    cur.close(); conn.close()
    result = []
    for row in rows:
        r = dict(row)
        try:    r["schedule"] = json.loads(r["schedule_json"])
        except: r["schedule"] = []
        result.append(r)
    if not result: return None
    return result if len(result) > 1 else result[0]


# ══════════════════════════════════════════
#  EMAIL LOGS
# ══════════════════════════════════════════
def log_email(patient_email, patient_name, timing, status, doctor_email=None):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(
        "INSERT INTO email_logs "
        "(patient_email,patient_name,timing,status,doctor_email) VALUES (%s,%s,%s,%s,%s)",
        (patient_email, patient_name, timing, status, doctor_email)
    )
    conn.commit()
    cur.close(); conn.close()


def get_email_logs(limit=50, doctor_email=None):
    conn = get_connection()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if doctor_email:
        cur.execute(
            "SELECT * FROM email_logs WHERE LOWER(doctor_email)=%s "
            "ORDER BY sent_at DESC LIMIT %s",
            (doctor_email.lower().strip(), limit),
        )
    else:
        cur.execute(
            "SELECT * FROM email_logs ORDER BY sent_at DESC LIMIT %s", (limit,)
        )
    rows = [dict(r) for r in cur.fetchall()]
    cur.close(); conn.close()
    return rows


def clear_patient_and_medicine_data(keep_users=True, keep_admin=True) -> dict:
    """Delete all patient-related data (patient_records, confirmed_medicines,
    prescription_schedules, email_logs). By default keeps the `users` table intact.

    If `keep_users` is False, all users will be deleted; if `keep_admin` is True
    and `keep_users` is False, the admin account `admin@medremind.com` will be preserved.

    Returns a dict with deletion counts.
    """
    conn = get_connection()
    cur  = conn.cursor()
    try:
        cur.execute("DELETE FROM confirmed_medicines")
        meds_deleted = cur.rowcount

        cur.execute("DELETE FROM prescription_schedules")
        sched_deleted = cur.rowcount

        cur.execute("DELETE FROM email_logs")
        logs_deleted = cur.rowcount

        cur.execute("DELETE FROM patient_records")
        patients_deleted = cur.rowcount

        users_deleted = 0
        if not keep_users:
            if keep_admin:
                cur.execute("DELETE FROM users WHERE email != %s", ("admin@medremind.com",))
            else:
                cur.execute("DELETE FROM users")
            users_deleted = cur.rowcount

        conn.commit()
        cur.close(); conn.close()
        return {
            "success": True,
            "deleted": {
                "confirmed_medicines": meds_deleted,
                "prescription_schedules": sched_deleted,
                "email_logs": logs_deleted,
                "patient_records": patients_deleted,
                "users": users_deleted,
            }
        }
    except Exception as e:
        conn.rollback(); cur.close(); conn.close()
        return {"success": False, "message": str(e)}