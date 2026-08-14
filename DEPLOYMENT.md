# Deployment Guide — ML Fair Team Formation System

## Prerequisites

- GitHub repository with this project
- Vercel account (free Hobby tier)
- Neon PostgreSQL account (free tier) or compatible PostgreSQL provider
- Vercel Blob store (free tier) for payment proofs

---

## Step 1: Prepare GitHub

1. Push this repository to GitHub.
2. Ensure `backend/data/Database-Fix-WMPL-S3.csv` is committed (it is tracked by git).
3. Ensure `.env` and `.env.local` are NOT committed (they are in `.gitignore`).

---

## Step 2: Create PostgreSQL Database

### Using Neon (Recommended — Free Tier)

1. Go to https://neon.tech and sign up.
2. Create a new project.
3. Create a database.
4. Copy the connection string. It looks like:
   ```
   postgresql+asyncpg://user:password@ep-xyz.neon.tech/dbname?sslmode=require
   ```
5. Save this as `DATABASE_URL`.

---

## Step 3: Create Vercel Blob Store

1. In your Vercel dashboard, go to your project.
2. Navigate to **Storage** → **Create Database** → **Blob**.
3. Copy the `BLOB_READ_WRITE_TOKEN`.
4. Save this token.

---

## Step 4: Configure Vercel Project

1. Go to https://vercel.com/new and import your GitHub repository.
2. Vercel will auto-detect the project configuration from `vercel.json`.
3. Before deploying, add the following **Environment Variables** in Vercel project settings:

### Required Environment Variables

| Variable | Value | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | From Neon |
| `SECRET_KEY` | `<random-long-string>` | Generate with `openssl rand -hex 32` |
| `CORS_ORIGINS` | `https://your-project.vercel.app` | Your Vercel domain |
| `FRONTEND_URL` | `https://your-project.vercel.app` | Your Vercel domain |
| `BLOB_READ_WRITE_TOKEN` | `<token>` | From Vercel Blob |
| `PAYMENT_METHOD` | `E-Money Dana/Link` | Or your preferred method |
| `PAYMENT_ACCOUNT_NUMBER` | `082141233543` | Your account number |
| `PAYMENT_ACCOUNT_NAME` | `Muhammad Syofiudin` | Your account name |
| `PAYMENT_AMOUNT` | `20000` | Payment amount |
| `MASTER_CSV_PATH` | `data/Database-Fix-WMPL-S3.csv` | Relative to backend root |
| `DEBUG` | `false` | Disable debug in production |

### Admin Emails (Optional)

Add `ADMIN_EMAILS` with comma-separated admin emails:
```
ADMIN_EMAILS=admin1@example.com,admin2@example.com
```

---

## Step 5: Deploy

1. Click **Deploy** in Vercel.
2. Vercel will:
   - Build the Next.js frontend from `frontend/`
   - Deploy the FastAPI backend as Python Serverless Functions at `/api/*`
   - Install Python dependencies from `api/requirements.txt`

---

## Step 6: Run Database Migration

After the first deployment:

1. The backend will auto-create tables on first request (via `lifespan`).
2. Go to your Vercel project → **Functions** → find the backend function.
3. Trigger a health check: `GET https://your-project.vercel.app/api/health`
4. This will initialize the database schema.

> Note: For production, consider adding explicit Alembic migrations. Currently, `Base.metadata.create_all` runs on every cold start.

---

## Step 7: Load Master Data

1. Login as admin: `POST /api/login` with admin email.
2. Process participants: `POST /api/admin/process-participants` with admin token.
3. This reads `backend/data/Database-Fix-WMPL-S3.csv` and upserts participants into PostgreSQL.

---

## Step 8: Test the Application

### Public Endpoints
```
GET  /                    → Frontend (Next.js)
GET  /api/health          → {"status": "healthy"}
GET  /api/config          → Public config
GET  /api/system-state    → System state
```

### Employee Flow
```
POST /api/login           → Login with email
GET  /api/me/ranking      → View ranking
POST /api/me/submit-payment → Upload payment proof
GET  /api/me/payment-status → Check payment status
GET  /api/me/team         → View team (requires PAID + all paid)
```

### Admin Flow
```
POST /api/admin/process-participants → Load CSV
POST /api/admin/generate-ranking     → Generate ranking
POST /api/admin/confirm-ranking      → Confirm ranking
POST /api/admin/generate-team        → Generate teams
POST /api/admin/verify-payment       → Verify payment
GET  /api/admin/dashboard            → Dashboard stats
GET  /api/admin/payments             → List payments
DELETE /api/admin/payments/{id}      → Delete payment
GET  /api/admin/audit-log            → Audit log
GET  /api/admin/ranking-versions     → Ranking history
GET  /api/admin/team-versions        → Team history
```

---

## Step 9: Local Development

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev  # runs on port 3636
```

Local `.env` files:
- Backend: `backend/.env`
- Frontend: `frontend/.env.local`

---

## Free Tier Limitations

| Service | Free Tier Limit | Impact |
|---|---|---|
| Vercel Hobby | 100GB bandwidth/month | Sufficient for internal use |
| Vercel Functions | 10s timeout (Hobby) | Team generation must complete within 10s |
| Neon PostgreSQL | 0.5GB storage | Sufficient for ~45 participants + history |
| Vercel Blob | 5GB storage | Sufficient for payment proofs |
| Vercel Blob | 1000 reads/day | Sufficient for internal use |

---

## Troubleshooting

### Database Connection Errors
- Verify `DATABASE_URL` uses `postgresql+asyncpg://` scheme.
- Ensure `sslmode=require` is appended for Neon.
- Check that the PostgreSQL database allows connections from Vercel IPs.

### Function Timeout
- If team generation exceeds 10s, consider:
  - Reducing `MAX_OPTIMIZATION_ITERATIONS`
  - Precomputing features
  - Using a Vercel Pro plan (60s timeout)

### CORS Errors
- Ensure `CORS_ORIGINS` includes your Vercel domain.
- For preview deployments, add the preview URL to `CORS_ORIGINS`.

### Payment Upload Fails
- Ensure `BLOB_READ_WRITE_TOKEN` is set.
- Check Vercel Blob store exists and token is valid.

### Master CSV Not Found
- Verify `MASTER_CSV_PATH` points to the correct relative path.
- Ensure `backend/data/Database-Fix-WMPL-S3.csv` is committed to git.
