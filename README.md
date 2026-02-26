# TrustBridge

**Secure multi-currency escrow & settlement platform for African digital commerce**

[![Status](https://img.shields.io/badge/status-early%20development-yellow)](https://github.com/yourusername/trustbridge-escrow)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## 📋 Table of Contents

- [Overview](#overview)
- [Core Features](#core-features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Development Roadmap](#-development-roadmap)
- [Important Warnings & Compliance](#important-warnings--compliance-notes-)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## Overview

TrustBridge enables trusted transactions between buyers and vendors by holding funds in the original currency (source-settled: NGN, GHS, KES, etc.) during escrow, avoiding exchange rate risk. Funds are released only after service confirmation, with an automatic 15% platform fee deducted (net of processor fees). A 14-day inactivity timer moves inactive transactions to a "dispute vault" for admin resolution.

Built as a **production-grade backend** with real-user intent in mind: concurrency-safe ledger, idempotent operations, audit trails, and compliance awareness (KYC, AML, licensing considerations).

**Current Status**: Phase 1 (Foundation & Project Setup) — Early development / MVP phase. Not yet production-deployed. **Strong compliance & legal warnings** apply (see below).

## Core Features

- **Source-Settled Escrow** — Funds held in original currency (no premature FX conversion)
- **15% Platform Fee** — Deducted only on successful release (net of Flutterwave fees)
- **14-Day Dispute Vault** — Auto-freeze on inactivity; admin-mediated resolution
- **Multi-Currency Support** — NGN, GHS, KES + real-time USD-view conversion (on-the-fly, cached rates)
- **Payment Methods** — Cards, bank transfers (via Flutterwave Standard/Direct Charge)
- **Authentication** — Firebase Auth (email/password, Google, Apple Sign In)
- **Payouts** — Vendor withdrawals via Flutterwave Transfer API (NUBAN, M-Pesa, etc.)
- **Webhooks** — Secure handling of Flutterwave events (charge.completed, transfers)
- **Ledger Integrity** — PostgreSQL with ACID transactions, DECIMAL for money

## Architecture Overview

### System Design

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Client    │────────▶│   FastAPI    │────────▶│ PostgreSQL  │
│ (Firebase)  │         │   Backend    │         │  Database   │
└─────────────┘         └──────────────┘         └─────────────┘
                              │  │
                              │  └──────────────▶┌─────────────┐
                              │                  │    Redis    │
                              │                  │   (Cache)   │
                              │                  └─────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │    Celery    │
                        │   Workers    │
                        └──────────────┘
                              │
                              ▼
                        ┌──────────────┐
                        │ Flutterwave  │
                        │     API      │
                        └──────────────┘
```

### Key Components

- **API Layer**: FastAPI with async endpoints, Pydantic validation, JWT middleware
- **Database Layer**: PostgreSQL with async SQLAlchemy, DECIMAL precision for money
- **Auth Layer**: Firebase Admin SDK for token verification and user management
- **Background Jobs**: Celery workers for webhooks, timers, and async operations
- **Cache Layer**: Redis for exchange rates, session data, and Celery broker
- **Payment Gateway**: Flutterwave for collections (hosted checkout) and payouts (Transfer API)

### Transaction Flow

1. **Vendor creates invoice** → Flutterwave payment link generated
2. **Customer pays** → Webhook marks funds as held in escrow (platform balance)
3. **Service confirmation** → Release endpoint deducts 15% fee → transfers 85% net to vendor
4. **Inactivity (14 days)** → Auto-dispute status; admin resolves (refund/transfer)

### Data Models (Core)

- **Users**: Firebase UID, email, role (buyer/vendor/admin), KYC status
- **Transactions**: Escrow state machine, amounts, currency, timestamps
- **Wallets**: User balances per currency
- **AuditLogs**: Immutable event trail for compliance
- **DisputeVault**: Frozen transactions awaiting resolution

## 🗺️ Development Roadmap

This project follows a 12-phase roadmap from foundation to production deployment. Each phase builds on the previous, ensuring a solid, compliant, and scalable platform.

### Phase 1: Foundation & Project Setup ✅ (Current)
**Goal**: Establish core infrastructure and development environment

- [x] Repository structure and Git setup
- [x] FastAPI skeleton with async support
- [x] PostgreSQL + SQLAlchemy 2.x (async)
- [x] Alembic migration framework
- [x] Docker & Docker Compose configuration
- [x] Environment configuration (.env management)
- [x] Structured logging (structlog)
- [ ] Sentry integration for error tracking

**Deliverables**: Working dev environment, health check endpoint, database connectivity

---

### Phase 2: Auth & Identity 🚧 (Next)
**Goal**: Secure user authentication and authorization

- [ ] Firebase Admin SDK integration
- [ ] JWT verification middleware
- [ ] User registration endpoint
- [ ] User profile management in PostgreSQL
- [ ] Role-based access control (buyer/vendor/admin)
- [ ] Protected route decorators
- [ ] User session management

**Deliverables**: Complete auth flow, user CRUD APIs, role enforcement

---

### Phase 3: Core Domain Models & Database Schema
**Goal**: Design and implement the escrow data model

- [ ] Escrow transaction model (state, amounts, parties)
- [ ] Wallet/balance tables (multi-currency support)
- [ ] Currency reference table
- [ ] Audit log schema (immutable event trail)
- [ ] Dispute vault table
- [ ] Database indexes for performance
- [ ] Complete Alembic migration history
- [ ] Data integrity constraints (foreign keys, checks)

**Deliverables**: Production-ready schema, migrations, ER diagram

---

### Phase 4: Currency & Exchange Rates
**Goal**: Real-time multi-currency support with caching

- [ ] Exchange rate fetching service (exchangerate-api.com or similar)
- [ ] Redis caching layer (TTL-based refresh)
- [ ] USD-view conversion utility functions
- [ ] Currency validation middleware
- [ ] Rate staleness detection
- [ ] Fallback mechanisms for API failures
- [ ] No stored FX values (on-the-fly conversion only)

**Deliverables**: Currency conversion API, cached rates, monitoring

---

### Phase 5: Payment Collection (Flutterwave In)
**Goal**: Accept payments from buyers via Flutterwave

- [ ] Flutterwave Standard/Inline integration
- [ ] Payment link generation endpoint
- [ ] Hosted checkout flow
- [ ] Webhook endpoint for `charge.completed` events
- [ ] Webhook signature verification
- [ ] Idempotency handling (duplicate webhook protection)
- [ ] Fund confirmation in database
- [ ] Payment status polling (backup to webhooks)

**Deliverables**: End-to-end payment collection, webhook processing

---

### Phase 6: Escrow State Machine
**Goal**: Implement transaction lifecycle management

- [ ] State definitions: `PENDING → FUNDED → ACTIVE → RELEASED/DISPUTED/REFUNDED`
- [ ] State transition validation rules
- [ ] Concurrency guards (optimistic locking or row-level locks)
- [ ] Event emission for state changes
- [ ] Audit trail for every transition
- [ ] Rollback mechanisms for failed transitions
- [ ] State machine visualization/documentation

**Deliverables**: Robust state machine, transition APIs, audit logs

---

### Phase 7: Release & Payout (Flutterwave Out)
**Goal**: Disburse funds to vendors after confirmation

- [ ] Fee calculation logic (15% platform fee, net of processor fees)
- [ ] Flutterwave Transfer API integration
- [ ] Payout initiation endpoint (vendor-triggered or auto)
- [ ] Payout status tracking
- [ ] Webhook handling for transfer events
- [ ] Payout audit trail
- [ ] Failed payout retry logic
- [ ] Vendor KYC verification check before payout

**Deliverables**: Complete payout flow, fee deduction, transfer tracking

---

### Phase 8: Background Jobs & Timers
**Goal**: Automate recurring tasks and async operations

- [ ] Celery + Redis setup (workers, beat scheduler)
- [ ] 14-day inactivity detection task
- [ ] Auto-dispute transition for inactive transactions
- [ ] Failed payout retry queue
- [ ] Exchange rate cache refresh job
- [ ] Webhook processing queue (async handling)
- [ ] Dead letter queue for failed tasks
- [ ] Task monitoring and alerting

**Deliverables**: Celery workers, scheduled tasks, retry mechanisms

---

### Phase 9: Admin Panel APIs
**Goal**: Provide admin tools for operations and support

- [ ] Dispute resolution endpoints (approve/reject/refund)
- [ ] Manual refund/transfer capabilities
- [ ] Transaction oversight dashboard API
- [ ] User management (suspend/activate accounts)
- [ ] KYC status management
- [ ] Audit log viewer API
- [ ] Platform metrics and reporting
- [ ] Admin role enforcement

**Deliverables**: Admin API suite, dispute resolution tools

---

### Phase 10: Security Hardening
**Goal**: Production-grade security and compliance

- [ ] Rate limiting (slowapi) on all endpoints
- [ ] Input validation audit (Pydantic schemas)
- [ ] OWASP Top 10 checklist review
- [ ] Secrets management (environment variables, vault)
- [ ] HTTPS enforcement (reverse proxy config)
- [ ] Webhook signature verification (all providers)
- [ ] SQL injection prevention audit
- [ ] CORS configuration
- [ ] Security headers (CSP, HSTS, etc.)
- [ ] Penetration testing (internal or third-party)

**Deliverables**: Security audit report, hardened configuration

---

### Phase 11: Testing Suite
**Goal**: Comprehensive test coverage for reliability

- [ ] Pytest configuration and fixtures
- [ ] Unit tests for business logic (>80% coverage)
- [ ] Integration tests for API endpoints
- [ ] Database transaction tests
- [ ] Flutterwave contract tests (mocked responses)
- [ ] Webhook simulation tests
- [ ] State machine transition tests
- [ ] Celery task tests
- [ ] Load testing (Locust or similar)
- [ ] CI pipeline integration (GitHub Actions)

**Deliverables**: Test suite with >80% coverage, CI/CD integration

---

### Phase 12: Observability, Deployment & Launch Prep
**Goal**: Production deployment and monitoring

- [ ] Structured logging audit (all critical paths)
- [ ] Metrics collection (Prometheus or similar)
- [ ] Health check endpoints (liveness, readiness)
- [ ] Docker Compose → cloud deployment (Railway/Render/AWS)
- [ ] CI/CD pipeline (automated testing, deployment)
- [ ] Database backup strategy
- [ ] Disaster recovery runbook
- [ ] Performance monitoring (APM)
- [ ] Alerting setup (PagerDuty, Slack)
- [ ] Documentation finalization
- [ ] Legal/compliance review
- [ ] Soft launch with limited users

**Deliverables**: Production deployment, monitoring, runbook, go-live

---

### Post-Launch Roadmap (Future Phases)

- **Phase 13**: Mobile app (Flutter/React Native)
- **Phase 14**: Advanced analytics and reporting
- **Phase 15**: Multi-language support (i18n)
- **Phase 16**: Cryptocurrency support (stablecoins)
- **Phase 17**: Marketplace integration (Shopify, WooCommerce)
- **Phase 18**: API for third-party integrations

---

### Progress Tracking

| Phase | Status | Completion | Target Date |
|-------|--------|------------|-------------|
| 1. Foundation | ✅ In Progress | 70% | Q1 2026 |
| 2. Auth & Identity | 🔜 Next | 0% | Q1 2026 |
| 3. Core Models | ⏳ Planned | 0% | Q2 2026 |
| 4. Currency Rates | ⏳ Planned | 0% | Q2 2026 |
| 5. Payment In | ⏳ Planned | 0% | Q2 2026 |
| 6. State Machine | ⏳ Planned | 0% | Q2 2026 |
| 7. Payout | ⏳ Planned | 0% | Q3 2026 |
| 8. Background Jobs | ⏳ Planned | 0% | Q3 2026 |
| 9. Admin Panel | ⏳ Planned | 0% | Q3 2026 |
| 10. Security | ⏳ Planned | 0% | Q4 2026 |
| 11. Testing | ⏳ Planned | 0% | Q4 2026 |
| 12. Deployment | ⏳ Planned | 0% | Q4 2026 |

**Legend**: ✅ In Progress | 🔜 Next | ⏳ Planned | ✔️ Complete

---

## Important Warnings & Compliance Notes ⚠️

**This is a fintech project handling real money — treat with extreme caution.**

### Regulatory Compliance

#### Nigeria (CBN Regulations)
- **PSP/MMO License Required**: Holding funds and charging fees may require a Payment Service Provider or Mobile Money Operator license
- **Capital Requirements**: Often ₦100M–₦2B+ capital/escrow deposit
- **Historical Context**: Many escrow platforms have faced shutdowns without proper authorization
- **Action Required**: Consult CBN guidelines and fintech lawyers before live deployment

#### Multi-Country Considerations
- **Ghana**: Bank of Ghana (BoG) payment system licensing
- **Kenya**: Central Bank of Kenya (CBK) payment service provider authorization
- **General**: Each market has unique regulatory requirements

### Technical Compliance

#### KYC (Know Your Customer)
- Vendors **must** complete KYC before payouts
- Flutterwave enforces transaction limits based on KYC tier
- Implement KYC status checks in payout flow
- Store KYC verification timestamps and documents

#### PCI DSS (Payment Card Industry)
- **Use hosted checkout** (Flutterwave Standard/Inline) to avoid direct card handling
- Maintains SAQ-A compliance scope (minimal requirements)
- Never store card numbers, CVV, or full PAN
- Log payment references only, not sensitive data

#### AML (Anti-Money Laundering)
- Implement transaction monitoring and pattern detection
- Set transaction limits and velocity checks
- Maintain audit trails for all financial operations
- Report suspicious activity per local regulations
- Document dispute resolution policies

### Financial Architecture Limitations

#### Flutterwave Escrow Constraints
- **No native long-hold escrow**: Funds held in main merchant/payout balance
- **State tracking in database**: Application-level escrow management
- **Settlement timing**: Understand Flutterwave settlement cycles
- **Balance management**: Monitor platform balance to ensure payout capacity

#### Risk Mitigation
- Implement reserve fund for operational liquidity
- Monitor balance vs. outstanding escrow obligations
- Set up alerts for low balance conditions
- Consider multi-provider strategy for redundancy

### Legal Disclaimers

⚠️ **NOT READY FOR PRODUCTION USE YET**

This repository is for:
- Learning and educational purposes
- Prototyping and proof-of-concept
- Development towards eventual compliant launch

**Before any live deployment or real-money testing:**
1. Consult a fintech lawyer in your target markets
2. Obtain necessary licenses and regulatory approvals
3. Complete security audit and penetration testing
4. Implement comprehensive insurance coverage
5. Establish legal entity with proper capitalization
6. Draft terms of service and privacy policy
7. Set up customer support and dispute resolution processes

**The authors are not liable for any financial, legal, or operational consequences arising from use of this software.**

## Tech Stack

### Backend
- **Python 3.11+** — Modern async/await support
- **FastAPI** — High-performance async web framework
- **Pydantic** — Data validation and settings management
- **SQLAlchemy 2.x** — Async ORM with type hints
- **Alembic** — Database migration management

### Database & Caching
- **PostgreSQL** — ACID-compliant relational database
- **Redis** — Caching layer for rates, sessions, and job queue

### Authentication & Security
- **Firebase Admin SDK** — JWT verification and user management
- **slowapi** — Rate limiting middleware
- **python-jose** — JWT token handling

### Payment Processing
- **Flutterwave API (v3)** — Payment collection and payouts

### Background Jobs
- **Celery** — Distributed task queue
- **Redis** — Message broker for Celery

### Observability
- **structlog** — Structured logging
- **Sentry** (planned) — Error tracking and monitoring

### Testing & Quality
- **Pytest** — Testing framework
- **httpx** — Async HTTP client for API tests
- **coverage** — Code coverage reporting

### DevOps
- **Docker & Docker Compose** — Containerization
- **GitHub Actions** (planned) — CI/CD pipeline

---

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **PostgreSQL 14+** ([Download](https://www.postgresql.org/download/))
- **Redis 6+** ([Download](https://redis.io/download))
- **Docker & Docker Compose** (optional, recommended) ([Download](https://www.docker.com/get-started))
- **Git** ([Download](https://git-scm.com/downloads))

Optional but recommended:
- **uv** (fast Python package manager) — `pip install uv`
- **Poetry** (alternative to uv) — `pip install poetry`

### Installation

#### Option 1: Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/trustbridge-escrow.git
cd trustbridge-escrow
```

2. Copy environment template:
```bash
cp .env.example .env
```

3. Edit `.env` with your credentials (see Configuration section below)

4. Start all services:
```bash
docker-compose up -d
```

5. Run database migrations:
```bash
docker-compose exec backend alembic upgrade head
```

6. Access the API:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### Option 2: Local Development (Manual)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/trustbridge-escrow.git
cd trustbridge-escrow
```

2. Create and activate virtual environment:
```bash
# Using uv (recommended)
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Or using venv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
# Using uv
uv pip install -r backend/requirements.txt

# Or using pip
pip install -r backend/requirements.txt
```

4. Set up PostgreSQL database:
```bash
# Create database
createdb trustbridge

# Or using psql
psql -U postgres -c "CREATE DATABASE trustbridge;"
```

5. Set up Redis (if not using Docker):
```bash
# macOS (Homebrew)
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Windows (WSL or native)
# Download from https://redis.io/download
```

6. Copy and configure environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

7. Run database migrations:
```bash
alembic upgrade head
```

8. Start the development server:
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

9. (Optional) Start Celery worker in a separate terminal:
```bash
celery -A backend.app.celery_worker worker --loglevel=info
```

10. (Optional) Start Celery beat scheduler:
```bash
celery -A backend.app.celery_worker beat --loglevel=info
```

### Configuration

Create a `.env` file in the project root with the following variables:

```bash
# Application
APP_NAME=TrustBridge
APP_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-here-change-in-production

# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/trustbridge

# Redis
REDIS_URL=redis://localhost:6379/0

# Firebase Authentication
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id

# Flutterwave
FLUTTERWAVE_PUBLIC_KEY=FLWPUBK_TEST-xxxxxxxxxxxxxxxx
FLUTTERWAVE_SECRET_KEY=FLWSECK_TEST-xxxxxxxxxxxxxxxx
FLUTTERWAVE_ENCRYPTION_KEY=FLWSECK_TESTxxxxxxxx
FLUTTERWAVE_WEBHOOK_SECRET=your-webhook-secret

# Exchange Rates API
EXCHANGE_RATE_API_KEY=your-api-key-here
EXCHANGE_RATE_API_URL=https://v6.exchangerate-api.com/v6

# Sentry (Optional)
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx

# Platform Settings
PLATFORM_FEE_PERCENTAGE=15.0
INACTIVITY_DAYS=14
```

#### Getting API Keys

1. **Firebase**:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create a project or select existing
   - Go to Project Settings → Service Accounts
   - Generate new private key (downloads JSON)
   - Extract values from JSON to `.env`

2. **Flutterwave**:
   - Sign up at [Flutterwave](https://dashboard.flutterwave.com/signup)
   - Go to Settings → API Keys
   - Copy test keys for development
   - Use live keys only in production

3. **Exchange Rate API**:
   - Sign up at [ExchangeRate-API](https://www.exchangerate-api.com/)
   - Free tier available (1,500 requests/month)
   - Copy API key from dashboard

### Running the Application

#### Development Mode

```bash
# Start FastAPI server with auto-reload
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Docker Compose
docker-compose up
```

#### Production Mode

```bash
# Start with Gunicorn (production ASGI server)
gunicorn backend.app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

### Verifying Installation

1. Check health endpoint:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-26T12:00:00Z",
  "database": "connected",
  "redis": "connected"
}
```

2. Access API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Project Structure

### Current Structure (Phase 1)

```
trustbridge-escrow/
├── .env                      # Environment variables (not in git)
├── .env.example              # Environment template
├── .gitignore
├── LICENSE
├── README.md
├── docker-compose.yml        # Docker services configuration
├── alembic.ini               # Alembic configuration
├── alembic/                  # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/             # Migration files
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py           # FastAPI application entry
│       ├── config.py         # Settings and configuration
│       ├── database.py       # Database connection
│       ├── logging.py        # Structured logging setup
│       ├── api/              # API endpoints
│       │   ├── __init__.py
│       │   └── health.py     # Health check endpoint
│       ├── middleware/       # Custom middleware
│       │   ├── __init__.py
│       │   └── logging.py    # Request/response logging
│       └── schemas/          # Pydantic schemas
│           └── __init__.py
└── tests/                    # Test suite
    └── __init__.py
```

### Target Structure (Production-Ready)

This is the complete structure we're building towards through all 12 phases:

```
trustbridge-escrow/
├── .env                      # Environment variables (not in git)
├── .env.example              # Environment template
├── .gitignore
├── LICENSE
├── README.md
├── CHANGELOG.md              # Version history
├── CONTRIBUTING.md           # Contribution guidelines
├── docker-compose.yml        # Development services
├── docker-compose.prod.yml   # Production services
├── Dockerfile                # Production container
├── requirements.txt          # Python dependencies
├── requirements-dev.txt      # Development dependencies
├── pytest.ini                # Pytest configuration
├── .flake8                   # Linting configuration
├── mypy.ini                  # Type checking configuration
│
├── alembic/                  # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/             # Migration files
│       ├── 001_initial_schema.py
│       ├── 002_add_users.py
│       └── ...
│
├── app/                      # Main application package
│   ├── __init__.py
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Settings via pydantic-settings
│   ├── database.py           # Async SQLAlchemy engine + session
│   ├── dependencies.py       # Shared FastAPI dependencies (get_db, etc.)
│   ├── logging_config.py     # Structlog setup
│   │
│   ├── api/                  # API layer
│   │   ├── __init__.py
│   │   └── v1/               # API version 1
│   │       ├── __init__.py
│   │       ├── router.py     # Mounts all v1 route groups
│   │       ├── auth.py       # Authentication endpoints
│   │       ├── users.py      # User management
│   │       ├── transactions.py  # Escrow transactions
│   │       ├── payments.py   # Payment collection
│   │       ├── payouts.py    # Vendor payouts
│   │       ├── webhooks.py   # Webhook receivers
│   │       ├── currencies.py # Currency operations
│   │       └── admin.py      # Admin operations
│   │
│   ├── models/               # SQLAlchemy ORM models (DB tables)
│   │   ├── __init__.py
│   │   ├── base.py           # Base model with common fields
│   │   ├── user.py           # User model
│   │   ├── transaction.py    # Transaction/escrow model
│   │   ├── wallet.py         # Wallet/balance model
│   │   ├── currency.py       # Currency reference
│   │   ├── audit_log.py      # Audit trail
│   │   ├── dispute.py        # Dispute vault
│   │   └── payout.py         # Payout records
│   │
│   ├── schemas/              # Pydantic schemas (request/response shapes)
│   │   ├── __init__.py
│   │   ├── user.py           # User schemas
│   │   ├── transaction.py    # Transaction schemas
│   │   ├── payment.py        # Payment schemas
│   │   ├── payout.py         # Payout schemas
│   │   ├── webhook.py        # Webhook schemas
│   │   └── common.py         # Shared schemas
│   │
│   ├── services/             # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth.py           # Firebase integration
│   │   ├── user.py           # User service
│   │   ├── currency.py       # Exchange rate service
│   │   ├── flutterwave.py    # Payment gateway client
│   │   ├── escrow.py         # Escrow state machine
│   │   ├── payout.py         # Payout service
│   │   ├── webhook.py        # Webhook processing
│   │   └── dispute.py        # Dispute resolution
│   │
│   ├── tasks/                # Celery background tasks
│   │   ├── __init__.py
│   │   ├── celery_app.py     # Celery configuration
│   │   ├── timers.py         # Inactivity detection
│   │   ├── payouts.py        # Retry failed payouts
│   │   └── rates.py          # Exchange rate refresh
│   │
│   ├── middleware/           # Custom middleware
│   │   ├── __init__.py
│   │   ├── logging.py        # Request/response logging
│   │   ├── auth.py           # JWT verification
│   │   ├── rate_limit.py     # Rate limiting
│   │   └── error_handler.py  # Global error handling
│   │
│   └── core/                 # Shared utilities, exceptions, constants
│       ├── __init__.py
│       ├── exceptions.py     # Custom exceptions
│       ├── constants.py      # Application constants
│       ├── security.py       # Security utilities
│       ├── validators.py     # Custom validators
│       └── enums.py          # Enums (TransactionState, etc.)
│
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── conftest.py           # Pytest fixtures
│   ├── test_health.py        # Health check tests
│   │
│   ├── unit/                 # Unit tests
│   │   ├── __init__.py
│   │   ├── test_currency.py
│   │   ├── test_escrow.py
│   │   ├── test_auth.py
│   │   └── test_validators.py
│   │
│   ├── integration/          # Integration tests
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   ├── test_webhooks.py
│   │   ├── test_payments.py
│   │   └── test_payouts.py
│   │
│   └── fixtures/             # Test data and mocks
│       ├── __init__.py
│       ├── flutterwave_mocks.py
│       └── sample_data.py
│
├── scripts/                  # Utility scripts
│   ├── seed_db.py            # Database seeding
│   ├── check_balance.py      # Platform balance checker
│   └── migrate_data.py       # Data migration helpers
│
└── docs/                     # Additional documentation
    ├── api.md                # API documentation
    ├── deployment.md         # Deployment guide
    ├── architecture.md       # Architecture decisions
    └── compliance.md         # Compliance checklist
```

### Key Architectural Decisions

1. **Flat app/ structure**: Keeps imports simple (`from app.models import User`)
2. **API versioning**: `/api/v1/` allows future breaking changes without disrupting clients
3. **Service layer**: Business logic separated from API routes for testability
4. **Pydantic schemas**: Separate from SQLAlchemy models for clean API contracts
5. **Core utilities**: Shared code in `core/` to avoid circular imports
6. **Task isolation**: Celery tasks in dedicated `tasks/` package
7. **Comprehensive testing**: Unit, integration, and fixture separation

---

## API Documentation

### Available Endpoints (Phase 1)

#### Health Check
```http
GET /health
```

Returns system health status including database and Redis connectivity.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-26T12:00:00Z",
  "database": "connected",
  "redis": "connected",
  "version": "0.1.0"
}
```

### Upcoming Endpoints (Future Phases)

See the [Development Roadmap](#-development-roadmap) for planned API endpoints in each phase.

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/unit/test_currency.py

# Run with verbose output
pytest -v

# Run integration tests only
pytest tests/integration/
```

### Test Coverage Goals

- Unit tests: >80% coverage
- Integration tests: All critical paths
- Contract tests: Flutterwave API mocks

---

## Deployment

### Docker Deployment

```bash
# Build production image
docker build -t trustbridge-backend:latest -f backend/Dockerfile .

# Run with Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### Cloud Platforms

#### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

#### Render
1. Connect GitHub repository
2. Create new Web Service
3. Set environment variables
4. Deploy automatically on push

#### AWS (ECS/Fargate)
- Use provided Dockerfile
- Configure RDS for PostgreSQL
- Configure ElastiCache for Redis
- Set up Application Load Balancer
- Configure CloudWatch for logging

---

## Contributing

We welcome contributions from the community! Whether it's bug fixes, new features, documentation improvements, or security enhancements, your help is appreciated.

### How to Contribute

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/trustbridge-escrow.git
   cd trustbridge-escrow
   ```

2. **Create a feature branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**
   - Write clean, documented code
   - Follow existing code style (PEP 8 for Python)
   - Add tests for new functionality
   - Update documentation as needed

4. **Run tests and linting**
   ```bash
   # Run tests
   pytest

   # Check code style
   black backend/
   isort backend/
   flake8 backend/

   # Type checking
   mypy backend/
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add amazing feature"
   ```

   Use conventional commit messages:
   - `feat:` New feature
   - `fix:` Bug fix
   - `docs:` Documentation changes
   - `test:` Test additions or changes
   - `refactor:` Code refactoring
   - `chore:` Maintenance tasks

6. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

7. **Open a Pull Request**
   - Provide a clear description of changes
   - Reference any related issues
   - Ensure CI checks pass

### Development Guidelines

- **Code Quality**: Maintain >80% test coverage
- **Security**: Never commit secrets or API keys
- **Documentation**: Update README and docstrings
- **Testing**: Add unit and integration tests
- **Performance**: Consider async/await patterns
- **Compliance**: Be mindful of fintech regulations

### Areas We Need Help

- 🧪 Test coverage improvements
- 📚 Documentation and tutorials
- 🔒 Security audits and improvements
- 🌍 Internationalization (i18n)
- 🐛 Bug fixes and issue triage
- ✨ Feature implementations (see roadmap)

### Code of Conduct

Be respectful, inclusive, and professional. We're building financial infrastructure that impacts real people's livelihoods.

---

## License

MIT License

Copyright (c) 2026 TrustBridge Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

### Important Note on Fintech Compliance

While this software is MIT licensed, **fintech compliance requirements override software licensing** in real-world use. You are responsible for:

- Obtaining necessary regulatory licenses
- Complying with local financial regulations
- Implementing proper KYC/AML procedures
- Securing appropriate insurance
- Consulting legal counsel

**The license does not grant permission to operate an unlicensed financial service.**

---

## Disclaimer

⚠️ **IMPORTANT LEGAL DISCLAIMER**

This project is provided for **educational and prototyping purposes only**. It is NOT ready for production use with real money.

- **No Warranty**: The software is provided "as is" without warranty of any kind
- **No Liability**: Authors are not liable for financial, legal, or operational consequences
- **Regulatory Compliance**: You are solely responsible for compliance with all applicable laws
- **Security**: No security guarantees are made; conduct your own audits
- **Financial Risk**: Use with real money at your own risk

**Before any production deployment:**
- Consult qualified legal counsel
- Obtain necessary licenses and approvals
- Complete comprehensive security audits
- Implement proper risk management
- Establish adequate capitalization

---

## Support & Community

### Getting Help

- 📖 **Documentation**: Check this README and `/docs` folder
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/trustbridge-escrow/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/trustbridge-escrow/issues)
- 📧 **Email**: [email]@trustbridge.dev (for security issues)

### Resources

- [Flutterwave API Documentation](https://developer.flutterwave.com/docs)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
- [Celery Documentation](https://docs.celeryproject.org/)

### Acknowledgments

Built with ❤️ in Umuahia, Nigeria, for the African digital commerce ecosystem.

Special thanks to:
- The FastAPI community
- Flutterwave for payment infrastructure
- All contributors and supporters

---

## Changelog

### v0.1.0 (Current - Phase 1)
- ✅ Initial project structure
- ✅ FastAPI application skeleton
- ✅ PostgreSQL + SQLAlchemy setup
- ✅ Alembic migrations
- ✅ Docker Compose configuration
- ✅ Health check endpoint
- ✅ Structured logging
- 🚧 Sentry integration (in progress)

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

---

**⭐ If you find this project useful, please consider starring the repository!**

**🚀 Ready to build the future of African fintech? Let's go!**