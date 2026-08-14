# ML Fair Team Formation System

A web-based system for automatically forming fair Mobile Legends competition teams using optimization algorithms, payment processing, and transparency features.

## Features

### User Features
- Registration and authentication with JWT token sessions
- CSV upload and validation
- Automatic rank and star normalization
- Player skill scoring with detailed breakdown
- Role capability and lane comfort calculation
- Optimal participant subset selection (multiples of 5)
- Randomized team formation with reproducibility
- Fairness calculation with transparent breakdown
- Payment upload with E-Money Dana/Link
- Team access gated by verified payment status
- Hero-themed team names (Alucard, Beatrix, Cecilion, Dyrroth, Edith, Floryn, Granger, Hylos, Irithel)
- Detailed transparency panels showing per-player skill score and role flexibility calculations
- Rankings page with full scoring breakdown

### Admin Features
- Dashboard with statistics overview
- CSV participant processing
- Ranking generation and confirmation
- Team generation with fairness optimization
- Payment verification and deletion
- Audit log for all admin actions
- Team version history with detail view
- Manual payment status override
- Delete payment to revoke user team access

### Technical Features
- Modern dark-themed dashboard with Tailwind CSS
- TypeScript frontend with React (Next.js 14)
- Async SQLAlchemy with PostgreSQL (production) / SQLite (development)
- Pydantic v2 settings and validation
- 67 backend tests passing
- CORS-enabled API
- Structured logging via audit logs
- Vercel-ready serverless deployment

---

## Architecture

```
GitHub
   ↓
Vercel (Single Project)
   ├── Frontend (Next.js)
   └── FastAPI Backend (/api/*)
          ↓
      PostgreSQL (Neon Free Tier)
          ↓
      Vercel Blob (Payment Proofs)
```

### Data Flow

```
data/Database-Fix-WMPL-S3.csv   (MASTER DATA — READ-ONLY)
         │
         ▼ READ / VALIDATE / UPSERT
PostgreSQL                      (APPLICATION DATABASE)
```

**Master CSV** is the authoritative source of participant data. It is read during `POST /api/admin/process-participants` and upserted into PostgreSQL. The CSV file itself is never modified by the application.

---

## Project Structure

```
ml-fair-team-formation/
├── api/
│   ├── index.py               ← Vercel Python Function entry
│   └── requirements.txt       ← Python deps for Vercel
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── deps.py
│   │   ├── config/
│   │   │   ├── constants.py
│   │   │   └── settings.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── ml/
│   │   ├── models/
│   │   │   └── models.py
│   │   ├── optimization/
│   │   │   ├── config/
│   │   │   │   └── role_config.py
│   │   │   ├── engines/
│   │   │   │   ├── role_compatibility_engine.py
│   │   │   │   ├── role_demand_analyzer.py
│   │   │   │   └── randomization_engine.py
│   │   │   ├── history/
│   │   │   │   └── history_manager.py
│   │   │   ├── participant_selector.py
│   │   │   ├── scoring/
│   │   │   │   ├── player_role_scorer.py
│   │   │   │   └── team_fairness_evaluator.py
│   │   │   └── team_optimizer.py
│   │   ├── preprocessing/
│   │   │   ├── features.py
│   │   │   └── validation.py
│   │   ├── repositories/
│   │   │   ├── audit_repository.py
│   │   │   ├── participant_repository.py
│   │   │   ├── payment_repository.py
│   │   │   ├── ranking_repository.py
│   │   │   ├── system_state_repository.py
│   │   │   └── team_repository.py
│   │   ├── schemas/
│   │   │   └── schemas.py
│   │   ├── services/
│   │   │   ├── payment_service.py
│   │   │   ├── ranking_service.py
│   │   │   ├── storage_service.py
│   │   │   ├── system_state_service.py
│   │   │   └── team_service.py
│   ├── tests/
│   ├── uploads/
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── AdminDashboard.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   ├── PaymentPage.tsx
│   │   │   ├── ProfilePage.tsx
│   │   │   ├── RankingsPage.tsx
│   │   │   ├── ResultsPage.tsx
│   │   │   └── shared/
│   │   │       ├── Card.tsx
│   │   │       ├── ErrorMessage.tsx
│   │   │       ├── LoadingSpinner.tsx
│   │   │       ├── NavButton.tsx
│   │   │       ├── StatusBadge.tsx
│   │   │       └── UserRankingCard.tsx
│   │   ├── lib/
│   │   │   ├── api.ts
│   │   │   ├── constants.ts
│   │   │   └── hooks/useAuth.ts
│   │   └── types/
│   │       └── index.ts
│   ├── package.json
│   ├── tailwind.config.js
│   ├── next.config.js
│   └── tsconfig.json
├── data/
│   └── Database-Fix-WMPL-S3.csv   ← READ-ONLY MASTER DATA
├── vercel.json
├── package.json
├── .gitignore
├── DEPLOYMENT.md
├── MASTER_DATA.md
└── README.md
```

---

## Setup Instructions

### Prerequisites

**Python 3.12 is required/recommended for this project.**

Do not use Python 3.14. Some scientific Python packages in the current dependency set may not provide compatible wheels for Python 3.14, causing installation to fall back to source builds.

### Backend

```bash
cd ~/ml-fair-team-formation/backend

/opt/homebrew/bin/python3.12 -m venv venv

source venv/bin/activate

python -m pip install --upgrade pip

pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

If Python 3.12 is not installed, install it with:

```bash
brew install python@3.12
```

### Frontend

```bash
cd ~/ml-fair-team-formation/frontend
npm install
npm run dev
```

Open http://localhost:3636

---

## CSV Format

Optional columns:
- `Player ID` — unique identifier for each participant. If missing, system auto-generates IDs like `P001`, `P002`, etc.
- `Name` — participant name. If missing, display will fall back to Player ID.

Required columns:
- Rank Saat Ini
- Perolehan Bintang pada Rank Saat Ini
- Rank Tertinggi
- Perolehan Bintang pada Rank Tertinggi
- Lane #1 Terbaik
- Seberapa nyaman menggunakan Lane #1
- Lane #2 Terbaik
- Seberapa nyaman menggunakan Lane #2

Example:
```csv
Player ID,Name,Rank Saat Ini,Perolehan Bintang pada Rank Saat Ini,Rank Tertinggi,Perolehan Bintang pada Rank Tertinggi,Lane #1 Terbaik,Seberapa nyaman menggunakan Lane #1,Lane #2 Terbaik,Seberapa nyaman menggunakan Lane #2
P001,Alex,Mythic,35,Mythical Glory,80,Jungle,5,Mid Lane,4
P002,Bella,Mythic,28,Mythical Honor,60,Gold Lane,5,EXP Lane,3
```

---

## Algorithm Explanation

### Player Skill Score

```
skill_score = 0.40 × current_rank_score
            + 0.20 × current_star_score
            + 0.25 × highest_rank_score
            + 0.15 × highest_star_score
```

### Role Flexibility Score

```
role_flexibility = 0.70 × normalized_primary_comfort
                 + 0.30 × normalized_secondary_comfort
```

Where `normalized_comfort = (comfort / 5.0) × 100`.

### Participant Selection

When total participants is not divisible by 5:
1. Calculate features for all participants
2. Evaluate candidate subsets
3. Select the subset that enables the fairest team formation
4. Consider role balance, skill variance, and player comfort

### Team Formation

1. Randomize selected participants using configurable seed
2. Generate candidate team configurations
3. Optimize for skill balance, role balance, and comfort
4. Reject configurations below fairness threshold
5. Select the fairest configuration
6. Assign hero-themed team names

### Fairness Score

```
Team Fairness = 0.40 × Skill Balance
              + 0.20 × Rank Balance
              + 0.40 × Role Balance
```

Where:
- `Skill Balance = max(0, 100 - skill_deviation × 3)`
- `Rank Balance = max(0, 100 - rank_std × 3)`
- `Role Balance = (covered_lanes / total_lanes) × 100`

---

## Configuration

Weights and settings are configurable via environment variables:

### Backend (`backend/.env` or Vercel env vars)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite+aiosqlite:///./ml_fair_teams.db` | Database connection |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | JWT signing secret |
| `CORS_ORIGINS` | `http://localhost:3636` | Comma-separated allowed origins |
| `FRONTEND_URL` | `http://localhost:3636` | Frontend origin |
| `DEBUG` | `true` | Enable debug mode |
| `CURRENT_RANK_WEIGHT` | `0.40` | Current rank influence |
| `CURRENT_STAR_WEIGHT` | `0.20` | Current stars influence |
| `HIGHEST_RANK_WEIGHT` | `0.25` | Highest rank influence |
| `HIGHEST_STAR_WEIGHT` | `0.15` | Highest stars influence |
| `MIN_FAIRNESS_THRESHOLD` | `85.0` | Minimum acceptable fairness |
| `MAX_OPTIMIZATION_ITERATIONS` | `5000` | Max optimization iterations |
| `DEFAULT_RANDOM_SEED` | `42` | Default random seed |
| `PAYMENT_METHOD` | `E-Money Dana/Link` | Payment method display |
| `PAYMENT_ACCOUNT_NUMBER` | `082141233543` | Payment account number |
| `PAYMENT_ACCOUNT_NAME` | `Muhammad Syofiudin` | Payment account name |
| `PAYMENT_AMOUNT` | `20000` | Required payment amount |
| `MASTER_CSV_PATH` | `data/Database-Fix-WMPL-S3.csv` | Path to master CSV |
| `BLOB_READ_WRITE_TOKEN` | `` | Vercel Blob token for payment proofs |
| `ADMIN_EMAILS` | `rebanialifito@gmail.com,rabbanialifito@gmail.com` | Comma-separated admin emails |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |

On Vercel, leave `NEXT_PUBLIC_API_URL` **unset** so the frontend uses relative `/api` paths automatically.

---

## API Endpoints

### Authentication
- `POST /api/login` - Login with email

### Participants
- `POST /api/admin/process-participants` - Process participant data from master CSV
- `GET /api/me/ranking` - Get current user ranking with breakdown

### Rankings
- `POST /api/admin/generate-ranking` - Generate rankings
- `POST /api/admin/confirm-ranking` - Confirm rankings
- `GET /api/admin/ranking-versions` - List ranking versions
- `GET /api/admin/ranking-versions/{version_id}` - Get ranking version detail
- `GET /api/rankings` - Get all rankings

### Teams
- `POST /api/admin/generate-team` - Generate teams
- `GET /api/admin/team-versions` - List team versions
- `GET /api/admin/team-versions/{version_id}` - Get team version detail
- `GET /api/me/team` - Get current user team
- `GET /api/teams` - Get all teams

### Payments
- `GET /api/me/payment` - Get current user payment
- `POST /api/me/submit-payment` - Submit payment proof
- `GET /api/me/payment-status` - Get payment status summary
- `GET /api/admin/payments` - List all payments
- `POST /api/admin/verify-payment` - Verify payment
- `DELETE /api/admin/payments/{payment_id}` - Delete payment

### System
- `GET /api/config` - Get current configuration
- `GET /api/health` - Health check
- `GET /api/system-state` - System state machine
- `GET /api/admin/audit-log` - Get audit log
- `GET /api/admin/dashboard` - Get dashboard statistics

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

Current test count: **67 tests passing**

---

## Payment Flow

1. User uploads payment proof via `POST /api/me/submit-payment`
2. Payment status becomes `PENDING`
3. Admin verifies payment via `POST /api/admin/verify-payment`
4. Payment status becomes `PAID`
5. All qualified participants must have `PAID` status before teams are visible
6. Admin can delete payment via `DELETE /api/admin/payments/{payment_id}`
7. Deleted payment revokes user's team access immediately

---

## Transparency Features

### Skill Score Breakdown
Each player's skill score is broken down into:
- Current Rank (40% weight)
- Current Star (20% weight)
- Highest Rank (25% weight)
- Highest Star (15% weight)

With raw scores, weights, contributions, and calculation formulas displayed.

### Role Flexibility Breakdown
Each player's role flexibility is broken down into:
- Primary Lane Comfort (70% weight)
- Secondary Lane Comfort (30% weight)

With normalized percentages, weights, contributions, and calculation formulas displayed.

### Team Fairness Breakdown
Each team's fairness score is broken down into:
- Skill Balance (40% weight)
- Rank Balance (20% weight)
- Role Balance (40% weight)

With average skill, global average, deviation, min/max, standard deviation, and lane coverage metrics.

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step deployment instructions to Vercel.

---

## Master Data

See [MASTER_DATA.md](MASTER_DATA.md) for documentation about `data/Database-Fix-WMPL-S3.csv`.

---

## Known Limitations

- Uses rank-based scoring (no historical match data)
- Optimization is heuristic for large participant counts
- Role balance requires at least one player per lane per team
- Team access requires all qualified participants to have verified payment
- Vercel Hobby tier has 10s function timeout

---

## Future Improvements

- Add supervised ML model with historical match data
- Support for custom role compositions
- Advanced constraint optimization with OR-Tools
- Email notifications for payment verification
- Real-time payment status updates via WebSocket
- Mobile app integration
