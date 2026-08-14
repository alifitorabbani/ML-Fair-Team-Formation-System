# Master Data Documentation

## Overview

`data/Database-Fix-WMPL-S3.csv` is the **MASTER DATABASE** for the ML Fair Team Formation System.

This file is the authoritative source of participant data. It must never be deleted, overwritten, or modified without explicit authorization.

---

## Location

```
ml-fair-team-formation/
└── data/
    └── Database-Fix-WMPL-S3.csv   ← READ-ONLY MASTER DATA
```

---

## Format

The CSV contains 16 columns:

| Column | Description |
|---|---|
| `Email Address` | Participant's personal email (unique identifier) |
| `Nama Lengkap` | Full name |
| `Username Mobile Legends` | MLBB username |
| `Rank Saat Ini` | Current rank (e.g., Mythic, Legend) |
| `Perolehan Bintang pada Rank Saat Ini` | Stars in current rank |
| `Rank Tertinggi` | Highest rank achieved |
| `Perolehan Bintang pada Rank Tertinggi` | Stars in highest rank |
| `Lane #1 Terbaik` | Primary lane preference |
| `Seberapa nyaman menggunakan Lane #1` | Comfort level (1-5) for primary lane |
| `Lane #2 Terbaik` | Secondary lane preference |
| `Seberapa nyaman menggunakan Lane #2` | Comfort level (1-5) for secondary lane |
| `Column 1` | Ignored |
| `Column 4` | Ignored |
| `Column 6` | Ignored |
| `Column 7` | Ignored |
| `Column 16` | Ignored |

---

## Statistics

- **Total rows**: 45 participants
- **Columns**: 16
- **Unique emails**: 45
- **Player IDs**: Auto-generated as `P001`–`P045` during processing

---

## Backup

Before any migration or deployment:

```bash
cp data/Database-Fix-WMPL-S3.csv data/Database-Fix-WMPL-S3.csv.backup
```

---

## Checksum Verification

```bash
md5sum data/Database-Fix-WMPL-S3.csv
# Expected: 7d5c072ee0d2b6d8bbbb1233d9a17b52

sha256sum data/Database-Fix-WMPL-S3.csv
# Expected: a175532ad8326b765ed2e4493278190ec0a1e4371a3bb13008086bf171352f60
```

---

## Import Flow

```
Database-Fix-WMPL-S3.csv
         │
         ▼ READ (read-only)
         ▼ VALIDATE (pandas)
         ▼ NORMALIZE (rank aliases, lane names)
         ▼ FEATURE ENGINEERING (skill score, role flexibility)
         ▼ UPSERT to PostgreSQL
```

### How to Import

1. Login as admin.
2. Call `POST /api/admin/process-participants`.
3. The system reads the CSV, validates it, and upserts participants into PostgreSQL.

### Upsert Behavior

- New participants are inserted.
- Existing participants (matched by email) are updated.
- Data such as rankings, teams, payments, and audit logs are **not** affected.

---

## Recovery

If the PostgreSQL database is lost:

1. Ensure `data/Database-Fix-WMPL-S3.csv` is intact.
2. Re-deploy or restart the application.
3. Call `POST /api/admin/process-participants` to re-import all participants.
4. Regenerate rankings and teams as needed.

---

## Rules

- **DO NOT** modify `Database-Fix-WMPL-S3.csv`.
- **DO NOT** delete `Database-Fix-WMPL-S3.csv`.
- **DO NOT** replace `Database-Fix-WMPL-S3.csv` with a generated file.
- **DO** create backups before migrations.
- **DO** verify checksums before and after deployment.

---

## Relationship to Other Databases

| Database | Purpose | Persistence |
|---|---|---|
| `Database-Fix-WMPL-S3.csv` | Master participant data | Git-tracked, permanent |
| `ml_fair_teams.db` | Local development SQLite | Ephemeral, ignored by git |
| PostgreSQL | Production application data | Persistent, hosted on Neon |
| Vercel Blob | Payment proof files | Persistent, hosted on Vercel |
