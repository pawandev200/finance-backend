# Finance Dashboard API

A production-structured backend for a finance dashboard system with role-based access control, JWT authentication, audit logging, and analytics APIs.

---

## Table of Contents

- [How Users Join the Platform](#how-users-join-the-platform)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Tech Stack & Why](#tech-stack--why)
- [Setup & Running](#setup--running)
- [API Reference](#api-reference)
- [Role & Permission Matrix](#role--permission-matrix)
- [System Design Decisions](#system-design-decisions)
- [Assumptions & Tradeoffs](#assumptions--tradeoffs)
- [What Would Change in Production](#what-would-change-in-production)

---

## How Users Join the Platform

This is the most important thing to understand about this system. There are **two distinct paths** for user creation, and they serve different purposes.

### Path 1 — Public Self-Registration (`POST /auth/register`)

```
Anyone on the internet
        │
        ▼
POST /auth/register
{ email, full_name, password }
        │
        ▼  role is ALWAYS forced to VIEWER here
        │  even if the request contains "role": "admin" — it is ignored
        ▼
User created with role = VIEWER
        │
        ▼
Login with POST /auth/login → get JWT tokens → access dashboard (read-only)
```

**Why force VIEWER on self-registration?**

This is a deliberate security design. In a finance system, you never want someone to self-assign elevated access. If `role` were accepted from the request body, a malicious actor could simply POST `{"role": "admin"}` and gain full system access. The `RegisterRequest` schema doesn't even include a `role` field — it's structurally impossible to pass one.

---

### Path 2 — Admin-Created Users (`POST /users/`)

```
Existing ADMIN user
        │
        ▼
POST /users/
Authorization: Bearer <admin_token>
{ email, full_name, password, role: "analyst" }  ← role chosen by admin
        │
        ▼
User created with the specified role
        │
        ▼
New user logs in → gets appropriate level of access
```

This is how you onboard team members who need ANALYST or ADMIN access. Only an existing Admin can do this.

---

### Path 3 — Admin Promotes an Existing User (`PATCH /users/{id}`)

```
User self-registers → gets VIEWER role
        │
        ▼
Admin reviews the user
        │
        ▼
PATCH /users/{user_id}
{ "role": "analyst" }
        │
        ▼
User now has ANALYST access on their next login
```

This is the promotion flow. A user can start as a VIEWER and be elevated later.

---

### How Does the Very First Admin Get Created?

The first admin has to be bootstrapped — this is true of every system (GitHub, AWS, etc.). In this project it's done via the seed script:

```bash
python scripts/seed.py
```

This creates `admin@finance.com / Admin@123` with ADMIN role directly in the database. In production, this would be a one-time CLI command or a secure setup wizard.

---

### Full User Journey (End to End)

```
1. New user hits POST /auth/register
   → Account created, role = VIEWER
   → Can log in and see dashboard summary + transaction list (read-only)

2. Admin logs in, sees the new user via GET /users/
   → Promotes them: PATCH /users/{id} { "role": "analyst" }

3. User logs in again
   → Now has ANALYST access: category breakdowns, trends, full analytics

4. If user needs to create/edit transactions:
   → Admin promotes to: { "role": "admin" }
   → User now has full CRUD access
```

---

## Architecture Overview

```
HTTP Request
     │
     ▼
Middleware chain
  RequestIDMiddleware  →  attaches X-Request-ID to every request
  CORSMiddleware       →  handles cross-origin headers
  RateLimiter          →  60 req/min per IP (configurable)
     │
     ▼
FastAPI Router  (app/api/v1/endpoints/)
     │  Schema validation via Pydantic v2
     │  Permission check via Depends(require_permission(...))
     ▼
Service Layer   (app/services/)
     │  Business rules, orchestration, audit logging
     ▼
Repository Layer (app/repositories/)
     │  All SQL queries — services never touch SQLAlchemy directly
     ▼
SQLAlchemy ORM  (app/models/)
     │
     ▼
SQLite (dev) / PostgreSQL (production)
```

### Layered Architecture — Why It Matters

| Layer | What it knows | What it doesn't know |
|---|---|---|
| Endpoint | HTTP verbs, request/response shapes | Business rules |
| Service | Business rules, what to do | How data is stored |
| Repository | SQL queries, how to fetch data | Business rules |
| Model | Table schema | Everything above |

This separation means you can change any layer independently. Want to switch from SQLite to PostgreSQL? Only the session config changes. Want to change a business rule? Only the service changes. The layers never bleed into each other.

---

## Project Structure

```
finance-backend/
├── main.py                          # App factory, middleware, startup hook
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
│
├── app/
│   ├── api/
│   │   ├── deps.py                  # DI: get_current_user, require_permission()
│   │   └── v1/
│   │       ├── router.py            # Aggregates all v1 routes
│   │       └── endpoints/
│   │           ├── auth.py          # register, login, refresh, me, logout
│   │           ├── users.py         # User CRUD (Admin only)
│   │           ├── transactions.py  # Financial records CRUD + filters
│   │           └── dashboard.py     # Summary, analytics, trends
│   │
│   ├── core/
│   │   ├── config.py                # Pydantic settings (all from .env)
│   │   ├── exceptions.py            # Custom HTTP exceptions (404, 403, 409...)
│   │   ├── permissions.py           # Role enum + permission matrix
│   │   └── security.py              # JWT creation/decoding, password hashing
│   │
│   ├── db/
│   │   ├── base.py                  # SQLAlchemy declarative base
│   │   ├── init_db.py               # Table creation on startup
│   │   └── session.py               # Engine + get_db() dependency
│   │
│   ├── middleware/
│   │   └── request_id.py            # Adds X-Request-ID to every request
│   │
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── transaction.py           # Includes soft-delete fields
│   │   └── audit_log.py             # Immutable action trail
│   │
│   ├── repositories/                # All SQL queries live here
│   │   ├── base.py                  # Generic BaseRepository[T]
│   │   ├── user_repo.py
│   │   └── transaction_repo.py      # Filtering, aggregation, trends
│   │
│   ├── schemas/                     # Pydantic v2 request/response models
│   │   ├── auth.py                  # RegisterRequest, LoginRequest, TokenResponse
│   │   ├── user.py                  # UserCreate, UserUpdate, UserResponse
│   │   ├── transaction.py           # TransactionCreate, Filter, Response
│   │   ├── dashboard.py             # Summary, Analytics, Trends schemas
│   │   └── common.py                # PaginatedResponse[T], MessageResponse
│   │
│   └── services/                    # Business logic layer
│       ├── user_service.py          # Registration, auth, user management
│       ├── transaction_service.py   # CRUD + soft delete
│       ├── dashboard_service.py     # Aggregation composition
│       └── audit_service.py         # Write and query audit logs
│
├── scripts/
│   └── seed.py                      # Creates demo users + 60 sample transactions
│
└── tests/
    ├── conftest.py                  # Fixtures, in-memory test DB, token helpers
    ├── test_auth.py                 # Login, token, /me tests
    ├── test_register.py             # Registration flow + role enforcement tests
    ├── test_transactions.py         # CRUD + RBAC tests
    └── test_dashboard.py            # Analytics + permission tests
```

---

## Tech Stack & Why

| Component | Choice | Reason |
|---|---|---|
| Framework | **FastAPI** | Auto-generates Swagger/ReDoc, built-in DI, Pydantic v2 validation, type-safe |
| ORM | **SQLAlchemy 2.0** | Works with SQLite, PostgreSQL, MySQL — swap connection string only |
| Validation | **Pydantic v2** | Field-level validators, clean 422 errors, schema-based docs |
| Auth | **python-jose + passlib** | Industry-standard JWT + secure password hashing |
| Rate limiting | **slowapi** | Per-IP rate limiting in 2 lines of code |
| Testing | **pytest + httpx** | Fast, fixtures-based, TestClient runs against real app |
| DB default | **SQLite** | Zero setup for dev/assessment; swap `DATABASE_URL` for Postgres |
| Container | **Docker + Compose** | One-command reproducible environment |

**Why FastAPI over Express.js?**
- Auto-generates interactive Swagger docs at `/docs` — a recruiter can test every endpoint in the browser without Postman
- Request validation errors are structured and readable by default
- Python type hints throughout make the code self-documenting
- Built-in dependency injection system makes auth and permission checks clean and composable

---

## Setup & Running

### Option 1 — Local (recommended)

```bash
# 1. Enter directory
cd finance-backend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (defaults work out of the box)
cp .env.example .env

# 5. Start server
uvicorn main:app --reload

# 6. (Optional) Seed demo data
python scripts/seed.py
```

**Swagger UI:** http://localhost:8000/docs  
**ReDoc:** http://localhost:8000/redoc  
**Health check:** http://localhost:8000/health

---

### Option 2 — Docker

```bash
docker-compose up --build
python scripts/seed.py
```

---

### Running Tests

```bash
pytest tests/ -v
```

Expected: **38 tests passing**

---

## Demo Credentials (after seeding)

| Role | Email | Password | What they can do |
|---|---|---|---|
| Admin | admin@finance.com | Admin@123 | Everything |
| Analyst | analyst@finance.com | Analyst@123 | Read transactions + full analytics |
| Viewer | viewer@finance.com | Viewer@123 | Read transactions + summary only |

Or register your own account:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "me@example.com", "full_name": "My Name", "password": "MyPass1"}'
```

---

## API Reference

All endpoints are prefixed with `/api/v1`. Full interactive docs at `/docs`.

### Authentication

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `POST` | `/auth/register` | No | Create account (always VIEWER) |
| `POST` | `/auth/login` | No | Get access + refresh tokens |
| `POST` | `/auth/refresh` | No (refresh token) | Get new access token |
| `GET` | `/auth/me` | Yes | Get your own profile |
| `POST` | `/auth/logout` | Yes | Logout (client discards token) |

**Register example:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@company.com",
    "full_name": "Alice Smith",
    "password": "SecurePass1"
  }'
```

**Login example:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@company.com", "password": "SecurePass1"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

Use the token in all subsequent requests:
```bash
curl http://localhost:8000/api/v1/dashboard/summary \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9..."
```

---

### Transactions

| Method | Endpoint | Required Role | Description |
|---|---|---|---|
| `POST` | `/transactions/` | Admin | Create transaction |
| `GET` | `/transactions/` | All | List with filters + pagination |
| `GET` | `/transactions/{id}` | All | Get single transaction |
| `PATCH` | `/transactions/{id}` | Admin | Update transaction |
| `DELETE` | `/transactions/{id}` | Admin | Soft delete |

**Filter parameters for `GET /transactions/`:**

| Param | Type | Description |
|---|---|---|
| `page` | int | Page number (default: 1) |
| `size` | int | Items per page (default: 20, max: 100) |
| `sort_by` | string | `date`, `amount`, `category`, `created_at` |
| `sort_order` | string | `asc` or `desc` |
| `type` | string | `income` or `expense` |
| `category` | string | Partial match |
| `date_from` | date | `YYYY-MM-DD` |
| `date_to` | date | `YYYY-MM-DD` |
| `search` | string | Searches notes + category text |

---

### Dashboard

| Method | Endpoint | Required Role | Description |
|---|---|---|---|
| `GET` | `/dashboard/summary` | All | KPI metrics (income, expense, net) |
| `GET` | `/dashboard/analytics` | Analyst, Admin | Category breakdowns + recent transactions |
| `GET` | `/dashboard/trends` | Analyst, Admin | Monthly income vs expense chart data |

**Summary response:**
```json
{
  "total_income": "12500.00",
  "total_expense": "4800.00",
  "net_balance": "7700.00",
  "transaction_count": 24,
  "income_count": 10,
  "expense_count": 14
}
```

**Analytics response (excerpt):**
```json
{
  "summary": { ... },
  "income_by_category": [
    { "category": "Salary", "total": "10000.00", "count": 2, "percentage": 80.0 },
    { "category": "Freelance", "total": "2500.00", "count": 3, "percentage": 20.0 }
  ],
  "expense_by_category": [ ... ],
  "recent_transactions": [ ... ]
}
```

**Trends response:**
```json
{
  "monthly_trends": [
    {
      "year": 2024, "month": 3, "month_label": "Mar 2024",
      "income": "5000.00", "expense": "2100.00", "net": "2900.00"
    }
  ],
  "period_label": "Last 12 months"
}
```

---

### Users (Admin only)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/users/` | Create user with any role |
| `GET` | `/users/` | List all users (paginated) |
| `GET` | `/users/{id}` | Get user by ID |
| `PATCH` | `/users/{id}` | Update role, status, or name |
| `GET` | `/users/{id}/audit-logs` | View user's full audit trail |

---

## Role & Permission Matrix

```
Permission                   VIEWER    ANALYST    ADMIN
──────────────────────────────────────────────────────────
transactions:read              Yes        Yes        Yes
transactions:create            No         No         Yes
transactions:update            No         No         Yes
transactions:delete            No         No         Yes
dashboard:summary              Yes        Yes        Yes
dashboard:analytics            No         Yes        Yes
dashboard:trends               No         Yes        Yes
users:read                     No         No         Yes
users:create                   No         No         Yes
users:update                   No         No         Yes
users:delete                   No         No         Yes
audit:read                     No         No         Yes
```

---

## System Design Decisions

### 1. Self-Registration Always Produces VIEWER

The `RegisterRequest` schema does not include a `role` field at all. This is intentional. Even if someone sends `"role": "admin"` in the JSON body, Pydantic ignores unknown fields and the endpoint hardcodes `role=Role.VIEWER`. This is defense in depth — the schema prevents it, and the service layer enforces it a second time.

### 2. Permission Matrix Instead of Role Checks

Most systems do this:
```python
if user.role == "admin":
    allow()
elif user.role == "analyst":
    allow_if_read()
```

This codebase uses a centralized permission matrix in `app/core/permissions.py`:
```python
ROLE_PERMISSIONS = {
    Role.VIEWER:  {"transactions:read", "dashboard:summary"},
    Role.ANALYST: {"transactions:read", "dashboard:summary", "dashboard:analytics", ...},
    Role.ADMIN:   {"transactions:read", "transactions:create", ... all permissions},
}
```

Adding a new role (e.g. `SUPER_ADMIN`, `AUDITOR`) is a single dict entry. No endpoint code changes. The permission check is a pure function: `has_permission(user.role, permission) → bool`.

### 3. Repository Pattern (Data Access Isolation)

Services never write a SQL query. Every database interaction goes through a repository method. This means:
- Services are testable without a database
- You can swap SQLAlchemy for another ORM by only changing repositories
- The query logic is centralized — no scattered `.filter()` calls across files

### 4. Soft Delete for Financial Records

```python
transaction.is_deleted = True
transaction.deleted_at = datetime.utcnow()
transaction.deleted_by_id = deleted_by_id
```

Records are never `DELETE`d from the database. Financial data must be recoverable for auditing, dispute resolution, and legal compliance. Every "deleted" record still shows in audit logs and can be restored by an admin directly in the DB if needed.

### 5. Audit Log as First-Class Feature

Every `CREATE`, `UPDATE`, `DELETE`, `LOGIN`, `LOGOUT`, and `REGISTER` event is written to `audit_logs` with:
- Who did it (`user_id`)
- What happened (`action`)
- What resource was affected (`resource`, `resource_id`)
- Before and after state (`old_value`, `new_value` as JSON)
- Request context (`ip_address`, `user_agent`)

This is not optional in financial systems. If a transaction gets modified, you need to know who changed it, when, and from what value to what.

### 6. API Versioning (`/api/v1/`)

All routes live under `/api/v1/`. When breaking changes are needed, a `/api/v2/` router is added in parallel. Existing clients on v1 continue working during a transition period. This is the industry standard (Stripe, GitHub, Twilio all version their APIs this way).

### 7. Access Token + Refresh Token Pair

| Token | Lifetime | Purpose |
|---|---|---|
| Access token | 30 minutes | Sent with every API request |
| Refresh token | 7 days | Used only to get a new access token |

Short-lived access tokens limit the damage if a token is stolen — it expires in 30 minutes maximum. The refresh token lets users stay logged in without re-entering credentials. In production, the refresh token should be stored in an HTTP-only cookie (not localStorage) and backed by a server-side Redis blocklist so it can be revoked on logout.

### 8. Request ID Middleware

Every request gets a unique `X-Request-ID` header (generated if not provided by the client). This propagates through the response. When a user reports "I got an error at 3pm", you grep your logs for their request ID and see the entire chain of what happened.

### 9. Generic Base Repository

```python
class BaseRepository(Generic[ModelType]):
    def get_by_id(self, id) ...
    def create(self, obj) ...
    def save(self, obj) ...
    def delete(self, obj) ...
```

Common operations are implemented once. `UserRepository` and `TransactionRepository` extend this and only add domain-specific queries. This eliminates boilerplate and keeps things DRY.

---

## Assumptions & Tradeoffs

| Decision | Assumption | Tradeoff |
|---|---|---|
| SQLite as default | Zero setup needed for evaluation | Not suitable for concurrent production writes; swap `DATABASE_URL` for PostgreSQL |
| Stateless JWT logout | Simpler, no Redis dependency | Tokens can't be truly invalidated until they expire; mitigate with short expiry |
| No email verification on register | Out of scope for this assessment | In production, send a verification email before activating the account |
| `strftime()` in trend queries | SQLite-specific date function | Needs to change to `EXTRACT()` for PostgreSQL; small migration required |
| CORS allows all origins | Suitable for local development | Production must restrict to known frontend origins |
| Soft delete only | Financial data must be recoverable | DB grows over time; mitigate with archival strategy for old deleted records |
| sha256_crypt for password hashing | passlib 1.7.4 + bcrypt 4.x incompatibility on Python 3.12 | In production, pin `bcrypt==4.0.1` and use `bcrypt` scheme for stronger hashing |
| Seed script creates first admin | Bootstrap problem exists in every system | In production, use a one-time secure CLI command or environment-based admin setup |
| Single `created_by_id` per transaction | One owner per record assumed | Multi-tenancy would add an `organization_id` field and row-level security |

---

## What Would Change in Production

| Area | Current (Assessment) | Production |
|---|---|---|
| Database | SQLite | PostgreSQL with connection pooling |
| Password hashing | sha256_crypt | bcrypt (pin bcrypt==4.0.1) |
| JWT logout | Client-side only | Redis token blocklist |
| Refresh token storage | Response body | HTTP-only Secure cookie |
| Email on register | None | Verification email via SendGrid/SES |
| Rate limiting | In-memory (per process) | Redis-backed (shared across instances) |
| Migrations | `init_db()` (auto create_all) | Alembic versioned migrations |
| Secrets | `.env` file | AWS Secrets Manager / Vault |
| CORS | Allow all origins | Allowlist of known frontend domains |
| Audit logs | Same database | Separate append-only store or CloudTrail |
| Monitoring | None | Structured JSON logs + Datadog/Sentry |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (see .env.example) | JWT signing key — **change in production** |
| `DATABASE_URL` | `sqlite:///./finance.db` | Any SQLAlchemy-compatible connection string |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `RATE_LIMIT_PER_MINUTE` | `60` | Max requests per IP per minute |
| `DEBUG` | `false` | Enables SQL query logging when true |
