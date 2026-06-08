# MedRemind — 4 reminder scripts

| File | Time | Timing |
|------|------|--------|
| `morning_8am.py` | 8 AM | Morning |
| `afternoon_1pm.py` | 1 PM | Afternoon |
| `evening_6pm.py` | 6 PM | Evening |
| `night_9pm.py` | 9 PM | Night |

## Layout

| File | Role |
|------|------|
| `.env` | Gmail + PostgreSQL passwords (copy from `.env.example`) |
| `config.py` | Reads `.env` only |
| `reminder_db.py` | DB connect, logs, active-medicine check |
| `reminder_mail.py` | Send email via Gmail |
| `morning_8am.py` etc. | **SQL query + cron `main()` only** |

## Setup

1. Copy `.env.example` → `.env` and fill values (including `DB_PASSWORD`).
2. Test: `python scripts/morning_8am.py`
3. Cron (Windows Task Scheduler): `python scripts/setup_windows_tasks.py`
