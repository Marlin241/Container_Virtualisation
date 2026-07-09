# Bibliothèque Numérique Microservices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and containerize a 3-microservice library platform (users, books, loans) with a React frontend, an Nginx gateway, and a Jenkins CI/CD pipeline, matching `docs/superpowers/specs/2026-07-08-bibliotheque-microservices-design.md`.

**Architecture:** Three independent FastAPI services (`users-service`, `books-service`, `loans-service`), each with its own PostgreSQL database, communicating with the frontend only through an Nginx gateway. `loans-service` calls `books-service` over HTTP to check/update availability. Authentication is a shared-secret JWT issued by `users-service` and validated locally by the other two.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, python-jose (JWT), passlib[bcrypt], httpx, pytest, PostgreSQL 16, React 18 (Vite), react-router-dom, axios, Nginx, Docker, Docker Compose, Jenkins.

## Global Constraints

- Each microservice (`users-service`, `books-service`, `loans-service`) has its own PostgreSQL database — no shared DB.
- Roles are exactly: `ETUDIANT`, `PROFESSEUR`, `PERSONNEL_ADMIN`.
- JWT is signed with a shared secret via the `JWT_SECRET` environment variable, algorithm `HS256`; payload is `{sub: "<user_id>", role: "<role>", exp: ...}`.
- Every backend microservice and the frontend each have their own `Dockerfile`.
- The gateway uses the official `nginx:alpine` image with a mounted config file — no custom Dockerfile for it.
- `loans-service` due date is `borrowed_at + 14 days`.
- No distributed transactions: sequential HTTP calls between services with explicit `409` (business conflict) / `503` (service unavailable) errors.
- No external Docker registry — Jenkins builds and deploys locally via `docker compose`.
- Jenkinsfile stages, in order: `Checkout` → `Build & Test` → `Build Docker Images` → `Deploy`.
- Tests use SQLite in-memory databases via FastAPI dependency overrides — never hit real Postgres in unit tests.

---

## Task 1: Repository scaffolding

**Files:**
- Create: `.gitignore`
- Create: `users-service/`, `books-service/`, `loans-service/`, `frontend/`, `gateway/`, `jenkins/` (empty directories, created implicitly by later tasks)

**Interfaces:**
- Produces: a `.gitignore` that keeps `__pycache__`, `node_modules`, `.env`, and DB volumes out of git.

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
.venv/

# Node
node_modules/
dist/

# Env
.env

# Editors/OS
.DS_Store
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add root .gitignore"
```

---

## Task 2: users-service — scaffold, User model, registration

**Files:**
- Create: `users-service/requirements.txt`
- Create: `users-service/app/__init__.py`
- Create: `users-service/app/database.py`
- Create: `users-service/app/models.py`
- Create: `users-service/app/schemas.py`
- Create: `users-service/app/security.py`
- Create: `users-service/app/main.py`
- Create: `users-service/tests/__init__.py`
- Create: `users-service/tests/conftest.py`
- Create: `users-service/tests/test_auth.py`

**Interfaces:**
- Produces: `models.UserRole` enum (`ETUDIANT`, `PROFESSEUR`, `PERSONNEL_ADMIN`), `models.User` SQLAlchemy model, `security.hash_password(password: str) -> str`, `security.verify_password(password: str, password_hash: str) -> bool`, FastAPI app with `POST /auth/register`.

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
pydantic[email]==2.9.2
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
bcrypt==4.0.1
pytest==8.2.0
httpx==0.27.0
```

Note: `bcrypt` is pinned explicitly (not left to `passlib[bcrypt]`'s own resolution) because `passlib==1.7.4` reads `bcrypt.__about__.__version__` to detect the backend version, an attribute removed in `bcrypt>=4.1`. Without this pin, pip installs the latest `bcrypt`, and every `hash_password`/`verify_password` call still works but logs a `(trapped) error reading bcrypt version` warning — `bcrypt==4.0.1` is the newest release that still has `__about__`, so hashing works with zero warnings and pristine test output.

Note: `sqlalchemy==2.0.36`, `psycopg2-binary==2.9.10`, and `pydantic[email]==2.9.2` (rather than `2.0.30`/`2.9.9`/`2.7.1`) are pinned to versions with prebuilt wheels for Python 3.13 — this task's `pip install -r requirements.txt` runs in whatever local Python the implementer has, which may be 3.13, while the Docker image (Task 5) pins `python:3.12-slim` regardless. `pydantic==2.7.1` in particular does not just warn on 3.13, it fails outright: `pydantic-core`'s Rust extension has no cp313 wheel at that version and its pinned `pyo3` cannot build against 3.13 (`the configured Python interpreter version (3.13) is newer than PyO3's maximum supported version`), so `pip install` errors out completely rather than degrading gracefully. All three pins stay within the same major/minor line the plan targets (SQLAlchemy 2.0.x, psycopg2 2.9.x, Pydantic 2.x).

- [ ] **Step 2: Create `app/__init__.py`** (empty file)

- [ ] **Step 3: Create `app/database.py`**

```python
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@users-db:5432/users_db",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Create `app/models.py`**

```python
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String

from .database import Base


class UserRole(str, enum.Enum):
    ETUDIANT = "ETUDIANT"
    PROFESSEUR = "PROFESSEUR"
    PERSONNEL_ADMIN = "PERSONNEL_ADMIN"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 5: Create `app/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from .models import UserRole


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: UserRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

- [ ] **Step 6: Create `app/security.py`**

```python
import os
from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext

JWT_SECRET = os.getenv("JWT_SECRET", "devsecret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
```

- [ ] **Step 7: Create `app/main.py`** (registration endpoint only for now)

```python
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db
from .security import hash_password


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="users-service", lifespan=lifespan)


@app.post("/auth/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = models.User(
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
```

Note: table creation runs inside a `lifespan` handler instead of at module import time. This matters because the default `DATABASE_URL` points at the real `users-db` Postgres host, which doesn't exist outside Docker Compose — if `Base.metadata.create_all(bind=engine)` ran at import time, `from app.main import app` would raise a connection error in any environment without that host resolvable (e.g. this task's own pytest run). Starlette's `TestClient(app)` only triggers `lifespan` when entered as a context manager (`with TestClient(app) as client:`); `tests/conftest.py` below instantiates it directly (`TestClient(app)`, no `with`), so `lifespan` never fires in tests and the production `create_all` is never attempted — table creation for tests is handled separately by the `setup_db` fixture against the SQLite test engine.

- [ ] **Step 8: Create `tests/__init__.py`** (empty file)

- [ ] **Step 9: Create `tests/conftest.py`**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    return TestClient(app)
```

- [ ] **Step 10: Write the failing tests — create `tests/test_auth.py`**

```python
def test_register_creates_user(client):
    response = client.post(
        "/auth/register",
        json={
            "full_name": "Awa Diop",
            "email": "awa@dit.sn",
            "password": "secret123",
            "role": "ETUDIANT",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "awa@dit.sn"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_rejected(client):
    payload = {
        "full_name": "Awa Diop",
        "email": "awa@dit.sn",
        "password": "secret123",
        "role": "ETUDIANT",
    }
    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
```

- [ ] **Step 11: Run tests to verify they fail before dependencies are installed**

Run: `cd users-service && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && pytest tests/test_auth.py -v`
Expected: both tests PASS (the implementation from Step 7 already exists). This confirms the scaffold is correct end-to-end.

If a test fails, re-check `app/main.py` and `app/schemas.py` against the code above before proceeding.

- [ ] **Step 12: Commit**

```bash
git add users-service/
git commit -m "feat(users-service): scaffold service and add registration endpoint"
```

---

## Task 3: users-service — login and JWT issuance

**Files:**
- Modify: `users-service/app/main.py`
- Modify: `users-service/tests/test_auth.py`

**Interfaces:**
- Consumes: `security.verify_password`, `security.create_access_token` (Task 2/existing `security.py`).
- Produces: `POST /auth/login` returning `schemas.TokenResponse`.

- [ ] **Step 1: Write the failing tests — append to `tests/test_auth.py`**

```python


def test_login_success_returns_token(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Awa Diop",
            "email": "awa@dit.sn",
            "password": "secret123",
            "role": "ETUDIANT",
        },
    )
    response = client.post("/auth/login", json={"email": "awa@dit.sn", "password": "secret123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_rejected(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Awa Diop",
            "email": "awa@dit.sn",
            "password": "secret123",
            "role": "ETUDIANT",
        },
    )
    response = client.post("/auth/login", json={"email": "awa@dit.sn", "password": "wrong"})
    assert response.status_code == 401


def test_login_unknown_email_rejected(client):
    response = client.post("/auth/login", json={"email": "nobody@dit.sn", "password": "secret123"})
    assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_auth.py -v`
Expected: `test_login_success_returns_token`, `test_login_wrong_password_rejected`, `test_login_unknown_email_rejected` FAIL with 404 (no `/auth/login` route yet).

- [ ] **Step 3: Implement — add to `app/main.py`** (insert after the `register` function)

```python
from .security import create_access_token, hash_password, verify_password


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(user.id, user.role.value)
    return schemas.TokenResponse(access_token=token)
```

Note: replace the existing `from .security import hash_password` import line at the top of `app/main.py` with the combined import shown above (do not have two separate import lines for the same module).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_auth.py -v`
Expected: all 5 tests in the file PASS.

- [ ] **Step 5: Commit**

```bash
git add users-service/
git commit -m "feat(users-service): add login endpoint issuing JWT"
```

---

## Task 4: users-service — JWT auth dependency and profile endpoints

**Files:**
- Create: `users-service/app/deps.py`
- Modify: `users-service/app/main.py`
- Create: `users-service/tests/test_users.py`

**Interfaces:**
- Consumes: `security.decode_access_token` (Task 2).
- Produces: `deps.get_current_payload(credentials) -> dict`, `deps.require_role(*roles) -> Depends callable`, `GET /users/me`, `GET /users/{user_id}`, `GET /users`.

- [ ] **Step 1: Create `app/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from .security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_payload(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        return decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def require_role(*roles: str):
    def checker(payload: dict = Depends(get_current_payload)) -> dict:
        if payload.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return payload

    return checker
```

- [ ] **Step 2: Write the failing tests — create `tests/test_users.py`**

```python
def register_and_login(client, role="ETUDIANT", email="user1@dit.sn"):
    client.post(
        "/auth/register",
        json={"full_name": "Test User", "email": email, "password": "secret123", "role": role},
    )
    response = client.post("/auth/login", json={"email": email, "password": "secret123"})
    return response.json()["access_token"]


def test_read_me_returns_current_user(client):
    token = register_and_login(client)
    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "user1@dit.sn"


def test_read_me_without_token_rejected(client):
    response = client.get("/users/me")
    assert response.status_code == 403  # HTTPBearer rejects missing credentials


def test_read_user_by_id_allowed_for_self(client):
    token = register_and_login(client)
    me = client.get("/users/me", headers={"Authorization": f"Bearer {token}"}).json()
    response = client.get(f"/users/{me['id']}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_read_user_by_id_forbidden_for_others(client):
    token_a = register_and_login(client, email="a@dit.sn")
    token_b = register_and_login(client, email="b@dit.sn")
    me_a = client.get("/users/me", headers={"Authorization": f"Bearer {token_a}"}).json()
    response = client.get(f"/users/{me_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 403


def test_list_users_requires_admin_role(client):
    token = register_and_login(client, role="ETUDIANT", email="student@dit.sn")
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_list_users_allowed_for_admin(client):
    token = register_and_login(client, role="PERSONNEL_ADMIN", email="admin@dit.sn")
    response = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_users.py -v`
Expected: all FAIL with 404 (no `/users/*` routes yet).

- [ ] **Step 4: Implement — add to `app/main.py`**

```python
from .deps import get_current_payload, require_role


@app.get("/users/me", response_model=schemas.UserOut)
def read_me(payload: dict = Depends(get_current_payload), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.get("/users/{user_id}", response_model=schemas.UserOut)
def read_user(user_id: int, payload: dict = Depends(get_current_payload), db: Session = Depends(get_db)):
    if int(payload["sub"]) != user_id and payload.get("role") != "PERSONNEL_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@app.get("/users", response_model=list[schemas.UserOut])
def list_users(payload: dict = Depends(require_role("PERSONNEL_ADMIN")), db: Session = Depends(get_db)):
    return db.query(models.User).all()
```

Important: `/users/me` must be declared **before** `/users/{user_id}` in the file, otherwise FastAPI/Starlette will try to parse `"me"` as an integer path parameter and return a 422 instead of matching `/users/me`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/ -v`
Expected: all tests in `test_auth.py` and `test_users.py` PASS (11 tests total).

- [ ] **Step 6: Commit**

```bash
git add users-service/
git commit -m "feat(users-service): add JWT auth dependency and profile endpoints"
```

---

## Task 5: users-service — Dockerfile and standalone verification

**Files:**
- Create: `users-service/Dockerfile`

**Interfaces:**
- Produces: a runnable container image exposing port 8000.

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Build and smoke-test the image standalone (uses SQLite fallback is not available here — this step only checks the image builds and boots; full DB-backed verification happens in Task 14 via Docker Compose)**

Run:
```bash
cd users-service
docker build -t users-service:local .
docker run --rm -e DATABASE_URL=sqlite:////tmp/users.db -e JWT_SECRET=devsecret -p 8001:8000 users-service:local &
sleep 3
curl -s -X POST http://localhost:8001/auth/register -H "Content-Type: application/json" \
  -d '{"full_name":"Smoke Test","email":"smoke@dit.sn","password":"secret123","role":"ETUDIANT"}'
docker stop $(docker ps -q --filter ancestor=users-service:local)
```

Expected: the `curl` call returns HTTP 201 with a JSON body containing `"email":"smoke@dit.sn"`. (SQLAlchemy's `postgresql+psycopg2://` URL scheme doesn't work with `sqlite:///`, but since this build only depends on `DATABASE_URL` being a valid SQLAlchemy URL, using `sqlite:////tmp/users.db` here is only for this standalone smoke test — Task 14 wires the real Postgres URL through Compose.)

- [ ] **Step 3: Commit**

```bash
git add users-service/Dockerfile
git commit -m "feat(users-service): add Dockerfile"
```

---

## Task 6: books-service — scaffold, Book model, create/list

**Files:**
- Create: `books-service/requirements.txt`
- Create: `books-service/app/__init__.py`
- Create: `books-service/app/database.py`
- Create: `books-service/app/models.py`
- Create: `books-service/app/schemas.py`
- Create: `books-service/app/security.py`
- Create: `books-service/app/deps.py`
- Create: `books-service/app/main.py`
- Create: `books-service/tests/__init__.py`
- Create: `books-service/tests/conftest.py`
- Create: `books-service/tests/test_books.py`

**Interfaces:**
- Produces: `models.Book`, `POST /books` (admin-only), `GET /books`, `deps.get_current_payload`, `deps.require_role` (same shape as `users-service`, independently duplicated per microservice).

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
pydantic==2.9.2
python-jose[cryptography]==3.3.0
pytest==8.2.0
httpx==0.27.0
```

- [ ] **Step 2: Create `app/__init__.py`** (empty file)

- [ ] **Step 3: Create `app/database.py`**

```python
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@books-db:5432/books_db",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Create `app/models.py`**

```python
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from .database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, nullable=False, index=True)
    isbn = Column(String, unique=True, nullable=False, index=True)
    total_copies = Column(Integer, nullable=False, default=1)
    available_copies = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 5: Create `app/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: str
    total_copies: int = Field(ge=1)


class BookUpdate(BaseModel):
    title: str
    author: str
    isbn: str
    total_copies: int = Field(ge=1)


class BookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    author: str
    isbn: str
    total_copies: int
    available_copies: int
    created_at: datetime


class AvailabilityUpdate(BaseModel):
    delta: int
```

- [ ] **Step 6: Create `app/security.py`**

```python
import os

from jose import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "devsecret")
JWT_ALGORITHM = "HS256"


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
```

- [ ] **Step 7: Create `app/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from .security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_payload(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        return decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def require_role(*roles: str):
    def checker(payload: dict = Depends(get_current_payload)) -> dict:
        if payload.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return payload

    return checker
```

- [ ] **Step 8: Create `app/main.py`** (create + list only for now)

```python
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import models, schemas
from .database import Base, engine, get_db
from .deps import get_current_payload, require_role


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="books-service", lifespan=lifespan)


@app.post("/books", response_model=schemas.BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    payload: schemas.BookCreate,
    _: dict = Depends(require_role("PERSONNEL_ADMIN")),
    db: Session = Depends(get_db),
):
    existing = db.query(models.Book).filter(models.Book.isbn == payload.isbn).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ISBN already exists")
    book = models.Book(
        title=payload.title,
        author=payload.author,
        isbn=payload.isbn,
        total_copies=payload.total_copies,
        available_copies=payload.total_copies,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@app.get("/books", response_model=list[schemas.BookOut])
def list_books(_: dict = Depends(get_current_payload), db: Session = Depends(get_db)):
    return db.query(models.Book).all()
```

- [ ] **Step 9: Create `tests/__init__.py`** (empty file)

- [ ] **Step 10: Create `tests/conftest.py`**

```python
import os

os.environ.setdefault("JWT_SECRET", "devsecret")

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    return TestClient(app)


def make_token(user_id: int, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": datetime.utcnow() + timedelta(hours=1)}
    return jwt.encode(payload, "devsecret", algorithm="HS256")


@pytest.fixture
def auth_header():
    def _make(user_id=1, role="ETUDIANT"):
        return {"Authorization": f"Bearer {make_token(user_id, role)}"}

    return _make
```

- [ ] **Step 11: Write the failing tests — create `tests/test_books.py`**

```python
def test_create_book_requires_admin_role(client, auth_header):
    response = client.post(
        "/books",
        json={"title": "Clean Code", "author": "Robert C. Martin", "isbn": "111", "total_copies": 2},
        headers=auth_header(role="ETUDIANT"),
    )
    assert response.status_code == 403


def test_create_book_as_admin_succeeds(client, auth_header):
    response = client.post(
        "/books",
        json={"title": "Clean Code", "author": "Robert C. Martin", "isbn": "111", "total_copies": 2},
        headers=auth_header(role="PERSONNEL_ADMIN"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["available_copies"] == 2


def test_create_book_duplicate_isbn_rejected(client, auth_header):
    payload = {"title": "Clean Code", "author": "Robert C. Martin", "isbn": "111", "total_copies": 2}
    client.post("/books", json=payload, headers=auth_header(role="PERSONNEL_ADMIN"))
    response = client.post("/books", json=payload, headers=auth_header(role="PERSONNEL_ADMIN"))
    assert response.status_code == 400


def test_list_books_returns_created_books(client, auth_header):
    client.post(
        "/books",
        json={"title": "Clean Code", "author": "Robert C. Martin", "isbn": "111", "total_copies": 2},
        headers=auth_header(role="PERSONNEL_ADMIN"),
    )
    response = client.get("/books", headers=auth_header())
    assert response.status_code == 200
    assert len(response.json()) == 1
```

- [ ] **Step 12: Run tests to verify they pass**

Run: `cd books-service && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && pytest tests/ -v`
Expected: all 4 tests PASS.

- [ ] **Step 13: Commit**

```bash
git add books-service/
git commit -m "feat(books-service): scaffold service with create/list book endpoints"
```

---

## Task 7: books-service — search, get-by-id, update, delete

**Files:**
- Modify: `books-service/app/main.py`
- Modify: `books-service/tests/test_books.py`

**Interfaces:**
- Produces: `GET /books/search`, `GET /books/{book_id}`, `PUT /books/{book_id}`, `DELETE /books/{book_id}`.

- [ ] **Step 1: Write the failing tests — append to `tests/test_books.py`**

```python


def create_sample_book(client, auth_header, isbn="111", title="Clean Code"):
    return client.post(
        "/books",
        json={"title": title, "author": "Robert C. Martin", "isbn": isbn, "total_copies": 2},
        headers=auth_header(role="PERSONNEL_ADMIN"),
    ).json()


def test_search_books_by_title(client, auth_header):
    create_sample_book(client, auth_header)
    response = client.get("/books/search?title=clean", headers=auth_header())
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_search_books_no_match_returns_empty_list(client, auth_header):
    create_sample_book(client, auth_header)
    response = client.get("/books/search?title=nomatch", headers=auth_header())
    assert response.status_code == 200
    assert response.json() == []


def test_get_book_by_id(client, auth_header):
    book = create_sample_book(client, auth_header)
    response = client.get(f"/books/{book['id']}", headers=auth_header())
    assert response.status_code == 200
    assert response.json()["isbn"] == "111"


def test_get_book_by_id_not_found(client, auth_header):
    response = client.get("/books/999", headers=auth_header())
    assert response.status_code == 404


def test_update_book_as_admin(client, auth_header):
    book = create_sample_book(client, auth_header)
    response = client.put(
        f"/books/{book['id']}",
        json={"title": "Clean Code 2nd Ed", "author": "Robert C. Martin", "isbn": "111", "total_copies": 3},
        headers=auth_header(role="PERSONNEL_ADMIN"),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Clean Code 2nd Ed"
    assert response.json()["available_copies"] == 3


def test_delete_book_as_admin(client, auth_header):
    book = create_sample_book(client, auth_header)
    response = client.delete(f"/books/{book['id']}", headers=auth_header(role="PERSONNEL_ADMIN"))
    assert response.status_code == 204
    response = client.get(f"/books/{book['id']}", headers=auth_header())
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_books.py -v`
Expected: the 6 new tests FAIL with 404 (routes don't exist yet).

- [ ] **Step 3: Implement — add to `app/main.py`** (after `list_books`)

```python
@app.get("/books/search", response_model=list[schemas.BookOut])
def search_books(
    title: str | None = None,
    author: str | None = None,
    isbn: str | None = None,
    _: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    query = db.query(models.Book)
    if title:
        query = query.filter(models.Book.title.ilike(f"%{title}%"))
    if author:
        query = query.filter(models.Book.author.ilike(f"%{author}%"))
    if isbn:
        query = query.filter(models.Book.isbn == isbn)
    return query.all()


@app.get("/books/{book_id}", response_model=schemas.BookOut)
def get_book(book_id: int, _: dict = Depends(get_current_payload), db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=schemas.BookOut)
def update_book(
    book_id: int,
    payload: schemas.BookUpdate,
    _: dict = Depends(require_role("PERSONNEL_ADMIN")),
    db: Session = Depends(get_db),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    borrowed = book.total_copies - book.available_copies
    book.title = payload.title
    book.author = payload.author
    book.isbn = payload.isbn
    book.total_copies = payload.total_copies
    book.available_copies = max(payload.total_copies - borrowed, 0)
    db.commit()
    db.refresh(book)
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    _: dict = Depends(require_role("PERSONNEL_ADMIN")),
    db: Session = Depends(get_db),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    db.delete(book)
    db.commit()
```

Critical ordering: `/books/search` MUST be defined before `/books/{book_id}` in the file (already the case here since `list_books` → `search_books` → `get_book`), otherwise Starlette matches `/books/search` against the `{book_id}` pattern first and returns a 422 instead of routing to search.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ -v`
Expected: all 10 tests in `test_books.py` PASS.

- [ ] **Step 5: Commit**

```bash
git add books-service/
git commit -m "feat(books-service): add search, get, update, delete endpoints"
```

---

## Task 8: books-service — availability endpoint and Dockerfile

**Files:**
- Modify: `books-service/app/main.py`
- Modify: `books-service/tests/test_books.py`
- Create: `books-service/Dockerfile`

**Interfaces:**
- Produces: `PATCH /books/{book_id}/availability` — request body `{"delta": int}`, returns `200` with updated `BookOut`, `404` if book missing, `409` if the resulting `available_copies` would be negative or exceed `total_copies`. This is the contract `loans-service` (Task 10) depends on.

- [ ] **Step 1: Write the failing tests — append to `tests/test_books.py`**

```python


def test_decrement_availability_succeeds(client, auth_header):
    book = create_sample_book(client, auth_header)
    response = client.patch(
        f"/books/{book['id']}/availability",
        json={"delta": -1},
        headers=auth_header(),
    )
    assert response.status_code == 200
    assert response.json()["available_copies"] == 1


def test_decrement_availability_below_zero_rejected(client, auth_header):
    book = create_sample_book(client, auth_header, isbn="222")
    client.patch(f"/books/{book['id']}/availability", json={"delta": -1}, headers=auth_header())
    client.patch(f"/books/{book['id']}/availability", json={"delta": -1}, headers=auth_header())
    response = client.patch(f"/books/{book['id']}/availability", json={"delta": -1}, headers=auth_header())
    assert response.status_code == 409


def test_increment_availability_succeeds(client, auth_header):
    book = create_sample_book(client, auth_header, isbn="333")
    client.patch(f"/books/{book['id']}/availability", json={"delta": -1}, headers=auth_header())
    response = client.patch(f"/books/{book['id']}/availability", json={"delta": 1}, headers=auth_header())
    assert response.status_code == 200
    assert response.json()["available_copies"] == 2


def test_availability_update_unknown_book_returns_404(client, auth_header):
    response = client.patch("/books/999/availability", json={"delta": -1}, headers=auth_header())
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_books.py -v`
Expected: the 4 new tests FAIL with 404 (route doesn't exist).

- [ ] **Step 3: Implement — add to `app/main.py`** (at the end of the file; also add `from sqlalchemy import update` to the existing import block at the top of the file)

```python
@app.patch("/books/{book_id}/availability", response_model=schemas.BookOut)
def update_availability(
    book_id: int,
    payload: schemas.AvailabilityUpdate,
    _: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    result = db.execute(
        update(models.Book)
        .where(
            models.Book.id == book_id,
            models.Book.available_copies + payload.delta >= 0,
            models.Book.available_copies + payload.delta <= models.Book.total_copies,
        )
        .values(available_copies=models.Book.available_copies + payload.delta)
    )
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Book not available")

    db.refresh(book)
    return book
```

Note: this uses a single atomic conditional `UPDATE ... WHERE ...` rather than a read-check-write, and requires `from sqlalchemy import update` added to `app/main.py`'s imports. A naive read-check-write (fetch `available_copies`, compute the new value in Python, check bounds, then commit) has a TOCTOU race under concurrent requests: two simultaneous borrows of the last copy of the same book could both read `available_copies=1`, both compute a valid new value, and both commit — silently overbooking instead of the second one correctly getting a 409. Folding the bounds check into the `UPDATE`'s `WHERE` clause makes the check-and-write atomic at the database level, closing that window on both SQLite (tests) and Postgres (production).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ -v`
Expected: all 14 tests in `test_books.py` PASS.

- [ ] **Step 5: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: Build and smoke-test the image standalone**

Run:
```bash
cd books-service
docker build -t books-service:local .
docker run --rm -e DATABASE_URL=sqlite:////tmp/books.db -e JWT_SECRET=devsecret -p 8002:8000 books-service:local &
sleep 3
curl -s http://localhost:8002/books -H "Authorization: Bearer invalid"
docker stop $(docker ps -q --filter ancestor=books-service:local)
```

Expected: HTTP 401 (`Invalid or expired token`) — confirms the container boots and JWT validation runs. Full success-path verification happens in Task 14.

- [ ] **Step 7: Commit**

```bash
git add books-service/
git commit -m "feat(books-service): add availability endpoint and Dockerfile"
```

---

## Task 9: loans-service — scaffold, Loan model, clients.py, borrow endpoint

**Files:**
- Create: `loans-service/requirements.txt`
- Create: `loans-service/app/__init__.py`
- Create: `loans-service/app/database.py`
- Create: `loans-service/app/models.py`
- Create: `loans-service/app/schemas.py`
- Create: `loans-service/app/security.py`
- Create: `loans-service/app/deps.py`
- Create: `loans-service/app/clients.py`
- Create: `loans-service/app/main.py`
- Create: `loans-service/tests/__init__.py`
- Create: `loans-service/tests/conftest.py`
- Create: `loans-service/tests/test_loans.py`

**Interfaces:**
- Consumes: `PATCH /books/{book_id}/availability` HTTP contract from Task 8 (`books-service`).
- Produces: `models.Loan`, `models.LoanStatus`, `clients.update_book_availability(book_id: int, delta: int, auth_header: str) -> None` (raises `clients.BookNotFound`, `clients.BookUnavailable`, or `clients.BooksServiceUnavailable`), `POST /loans`.

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
pydantic==2.9.2
python-jose[cryptography]==3.3.0
httpx==0.27.0
pytest==8.2.0
```

- [ ] **Step 2: Create `app/__init__.py`** (empty file)

- [ ] **Step 3: Create `app/database.py`**

```python
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@loans-db:5432/loans_db",
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Create `app/models.py`**

```python
import enum
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Enum, Integer

from .database import Base


class LoanStatus(str, enum.Enum):
    EN_COURS = "EN_COURS"
    RETOURNE = "RETOURNE"


class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    borrowed_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=14))
    returned_at = Column(DateTime, nullable=True)
    status = Column(Enum(LoanStatus), nullable=False, default=LoanStatus.EN_COURS)
```

- [ ] **Step 5: Create `app/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .models import LoanStatus


class LoanCreate(BaseModel):
    book_id: int


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    book_id: int
    user_id: int
    borrowed_at: datetime
    due_date: datetime
    returned_at: datetime | None
    status: LoanStatus
```

- [ ] **Step 6: Create `app/security.py`**

```python
import os

from jose import jwt

JWT_SECRET = os.getenv("JWT_SECRET", "devsecret")
JWT_ALGORITHM = "HS256"


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
```

- [ ] **Step 7: Create `app/deps.py`**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from .security import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_payload(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    try:
        return decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
```

- [ ] **Step 8: Create `app/clients.py`**

```python
import os

import httpx

BOOKS_SERVICE_URL = os.getenv("BOOKS_SERVICE_URL", "http://books-service:8000")


class BookNotFound(Exception):
    pass


class BookUnavailable(Exception):
    pass


class BooksServiceUnavailable(Exception):
    pass


def update_book_availability(book_id: int, delta: int, auth_header: str) -> None:
    try:
        response = httpx.patch(
            f"{BOOKS_SERVICE_URL}/books/{book_id}/availability",
            json={"delta": delta},
            headers={"Authorization": auth_header},
            timeout=5.0,
        )
    except httpx.RequestError as exc:
        raise BooksServiceUnavailable(str(exc)) from exc

    if response.status_code == 404:
        raise BookNotFound(f"Book {book_id} not found")
    if response.status_code == 409:
        raise BookUnavailable(f"Book {book_id} not available")
    response.raise_for_status()
```

- [ ] **Step 9: Create `app/main.py`** (borrow endpoint only for now)

```python
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, status
from sqlalchemy.orm import Session

from . import clients, models, schemas
from .database import Base, engine, get_db
from .deps import get_current_payload


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="loans-service", lifespan=lifespan)


@app.post("/loans", response_model=schemas.LoanOut, status_code=status.HTTP_201_CREATED)
def borrow_book(
    payload_body: schemas.LoanCreate,
    request: Request,
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    auth_header = request.headers["authorization"]
    try:
        clients.update_book_availability(payload_body.book_id, -1, auth_header)
    except clients.BookNotFound:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    except clients.BookUnavailable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Book not available")
    except clients.BooksServiceUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Books service unavailable")

    loan = models.Loan(book_id=payload_body.book_id, user_id=int(payload["sub"]))
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan
```

- [ ] **Step 10: Create `tests/__init__.py`** (empty file)

- [ ] **Step 11: Create `tests/conftest.py`**

```python
import os

os.environ.setdefault("JWT_SECRET", "devsecret")

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    return TestClient(app)


def make_token(user_id: int, role: str) -> str:
    payload = {"sub": str(user_id), "role": role, "exp": datetime.utcnow() + timedelta(hours=1)}
    return jwt.encode(payload, "devsecret", algorithm="HS256")


@pytest.fixture
def auth_header():
    def _make(user_id=1, role="ETUDIANT"):
        return {"Authorization": f"Bearer {make_token(user_id, role)}"}

    return _make
```

- [ ] **Step 12: Write the failing tests — create `tests/test_loans.py`**

```python
from unittest.mock import patch

from app import clients


def test_borrow_book_creates_loan(client, auth_header):
    with patch("app.main.clients.update_book_availability") as mock_update:
        mock_update.return_value = None
        response = client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
    assert response.status_code == 201
    body = response.json()
    assert body["book_id"] == 1
    assert body["status"] == "EN_COURS"
    mock_update.assert_called_once()
    called_args = mock_update.call_args.args
    assert called_args[0] == 1
    assert called_args[1] == -1


def test_borrow_unavailable_book_returns_409(client, auth_header):
    with patch("app.main.clients.update_book_availability", side_effect=clients.BookUnavailable("no copies")):
        response = client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
    assert response.status_code == 409


def test_borrow_unknown_book_returns_404(client, auth_header):
    with patch("app.main.clients.update_book_availability", side_effect=clients.BookNotFound("missing")):
        response = client.post("/loans", json={"book_id": 999}, headers=auth_header(user_id=1))
    assert response.status_code == 404


def test_borrow_when_books_service_down_returns_503(client, auth_header):
    with patch(
        "app.main.clients.update_book_availability",
        side_effect=clients.BooksServiceUnavailable("connection refused"),
    ):
        response = client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
    assert response.status_code == 503
```

- [ ] **Step 13: Run tests to verify they fail**

Run: `cd loans-service && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && pytest tests/ -v`
Expected: all 4 tests PASS (implementation from Step 9 already exists) — this confirms the scaffold end-to-end, including the mocking pattern used by later tasks.

- [ ] **Step 14: Commit**

```bash
git add loans-service/
git commit -m "feat(loans-service): scaffold service with borrow endpoint"
```

---

## Task 10: loans-service — return endpoint

**Files:**
- Modify: `loans-service/app/main.py`
- Modify: `loans-service/tests/test_loans.py`

**Interfaces:**
- Produces: `PATCH /loans/{loan_id}/return`.

- [ ] **Step 1: Write the failing tests — append to `tests/test_loans.py`**

```python


def test_return_book_marks_loan_returned(client, auth_header):
    with patch("app.main.clients.update_book_availability"):
        create_response = client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
    loan_id = create_response.json()["id"]

    with patch("app.main.clients.update_book_availability"):
        response = client.patch(f"/loans/{loan_id}/return", headers=auth_header(user_id=1))
    assert response.status_code == 200
    assert response.json()["status"] == "RETOURNE"
    assert response.json()["returned_at"] is not None


def test_return_unknown_loan_returns_404(client, auth_header):
    response = client.patch("/loans/999/return", headers=auth_header(user_id=1))
    assert response.status_code == 404


def test_return_already_returned_loan_rejected(client, auth_header):
    with patch("app.main.clients.update_book_availability"):
        create_response = client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
    loan_id = create_response.json()["id"]

    with patch("app.main.clients.update_book_availability"):
        client.patch(f"/loans/{loan_id}/return", headers=auth_header(user_id=1))
        response = client.patch(f"/loans/{loan_id}/return", headers=auth_header(user_id=1))
    assert response.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_loans.py -v`
Expected: the 3 new tests FAIL with 404 (route doesn't exist).

- [ ] **Step 3: Implement — add to `app/main.py`** (after `borrow_book`)

```python
@app.patch("/loans/{loan_id}/return", response_model=schemas.LoanOut)
def return_book(
    loan_id: int,
    request: Request,
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    loan = db.query(models.Loan).filter(models.Loan.id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.status == models.LoanStatus.RETOURNE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Loan already returned")

    auth_header = request.headers["authorization"]
    try:
        clients.update_book_availability(loan.book_id, 1, auth_header)
    except clients.BooksServiceUnavailable:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Books service unavailable")
    except (clients.BookNotFound, clients.BookUnavailable):
        pass

    loan.status = models.LoanStatus.RETOURNE
    loan.returned_at = datetime.utcnow()
    db.commit()
    db.refresh(loan)
    return loan
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ -v`
Expected: all 7 tests in `test_loans.py` PASS.

- [ ] **Step 5: Commit**

```bash
git add loans-service/
git commit -m "feat(loans-service): add return endpoint"
```

---

## Task 11: loans-service — history endpoint with role filtering, Dockerfile

**Files:**
- Modify: `loans-service/app/main.py`
- Modify: `loans-service/tests/test_loans.py`
- Create: `loans-service/Dockerfile`

**Interfaces:**
- Produces: `GET /loans` (optional `?user_id=` query param, admin-only).

- [ ] **Step 1: Write the failing tests — append to `tests/test_loans.py`**

```python


def test_list_loans_filters_by_user_for_non_admin(client, auth_header):
    with patch("app.main.clients.update_book_availability"):
        client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
        client.post("/loans", json={"book_id": 2}, headers=auth_header(user_id=2))

    response = client.get("/loans", headers=auth_header(user_id=1))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["user_id"] == 1


def test_list_loans_admin_sees_all(client, auth_header):
    with patch("app.main.clients.update_book_availability"):
        client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
        client.post("/loans", json={"book_id": 2}, headers=auth_header(user_id=2))

    response = client.get("/loans", headers=auth_header(user_id=99, role="PERSONNEL_ADMIN"))
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_loans_admin_can_filter_by_user_id(client, auth_header):
    with patch("app.main.clients.update_book_availability"):
        client.post("/loans", json={"book_id": 1}, headers=auth_header(user_id=1))
        client.post("/loans", json={"book_id": 2}, headers=auth_header(user_id=2))

    response = client.get("/loans?user_id=2", headers=auth_header(user_id=99, role="PERSONNEL_ADMIN"))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["user_id"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_loans.py -v`
Expected: the 3 new tests FAIL with 404 (route doesn't exist).

- [ ] **Step 3: Implement — add to `app/main.py`** (at the end of the file)

```python
@app.get("/loans", response_model=list[schemas.LoanOut])
def list_loans(
    user_id: int | None = None,
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
):
    query = db.query(models.Loan)
    if payload.get("role") == "PERSONNEL_ADMIN":
        if user_id is not None:
            query = query.filter(models.Loan.user_id == user_id)
    else:
        query = query.filter(models.Loan.user_id == int(payload["sub"]))
    return query.all()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/ -v`
Expected: all 10 tests in `test_loans.py` PASS.

- [ ] **Step 5: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 6: Commit**

```bash
git add loans-service/
git commit -m "feat(loans-service): add loan history endpoint and Dockerfile"
```

---

## Task 12: Docker Compose — wire backend services and databases

**Files:**
- Create: `docker-compose.yml`

**Interfaces:**
- Produces: a running stack reachable at `users-service:8000`, `books-service:8000`, `loans-service:8000` on the Compose network, backed by three separate Postgres containers. Consumed by Task 13 (gateway) and Task 17 (Jenkins).

- [ ] **Step 1: Create `docker-compose.yml`**

```yaml
services:
  users-db:
    image: postgres:16
    environment:
      POSTGRES_DB: users_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - users_db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  books-db:
    image: postgres:16
    environment:
      POSTGRES_DB: books_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - books_db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  loans-db:
    image: postgres:16
    environment:
      POSTGRES_DB: loans_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - loans_db_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  users-service:
    build: ./users-service
    environment:
      DATABASE_URL: postgresql+psycopg2://postgres:postgres@users-db:5432/users_db
      JWT_SECRET: ${JWT_SECRET:-devsecret}
    depends_on:
      users-db:
        condition: service_healthy

  books-service:
    build: ./books-service
    environment:
      DATABASE_URL: postgresql+psycopg2://postgres:postgres@books-db:5432/books_db
      JWT_SECRET: ${JWT_SECRET:-devsecret}
    depends_on:
      books-db:
        condition: service_healthy

  loans-service:
    build: ./loans-service
    environment:
      DATABASE_URL: postgresql+psycopg2://postgres:postgres@loans-db:5432/loans_db
      JWT_SECRET: ${JWT_SECRET:-devsecret}
      BOOKS_SERVICE_URL: http://books-service:8000
    depends_on:
      loans-db:
        condition: service_healthy
      books-service:
        condition: service_started

volumes:
  users_db_data:
  books_db_data:
  loans_db_data:
```

Note: each `*-db` service gets a `pg_isready` healthcheck, and every backend service's `depends_on` waits on `condition: service_healthy` for its own database (not just container-started). Without this, `docker compose up -d --build` races the FastAPI `lifespan` handler's `Base.metadata.create_all` against Postgres's cold-init time — confirmed by direct test: on a fresh `docker compose up`, `users-service` and `loans-service` exited (code 3) because they tried to connect before Postgres was accepting connections yet, and neither self-recovered (no `restart` policy), leaving the stack silently half-up. The healthcheck-gated `depends_on` makes a single `docker compose up -d --build` reliably bring up the whole stack, matching this project's hard requirement. `loans-service` additionally depends on `books-service` with `condition: service_started` (not `service_healthy` — `books-service` has no HTTP-level healthcheck defined, container-started is sufficient here since `loans-service` only calls it lazily on the first borrow/return request, by which point it will be up).

- [ ] **Step 2: Bring up the backend stack and verify end-to-end through real Postgres**

Run:
```bash
docker compose up -d --build users-db books-db loans-db users-service books-service loans-service
sleep 5
curl -s -X POST http://localhost:8000/auth/register 2>/dev/null || echo "users-service has no host port yet — check via docker compose exec instead"
docker compose exec users-service curl -s -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" \
  -d '{"full_name":"Admin","email":"admin@dit.sn","password":"secret123","role":"PERSONNEL_ADMIN"}'
```

Expected: JSON response with `"email":"admin@dit.sn"` and HTTP 201, proving `users-service` talks to real Postgres. Repeat similarly for `books-service` (`docker compose exec books-service curl ...`) once a token is obtained. Tear down with `docker compose down -v` after verifying.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add docker-compose wiring backend services and databases"
```

---

## Task 13: Gateway — Nginx reverse proxy config

**Files:**
- Create: `gateway/nginx.conf`
- Modify: `docker-compose.yml`

**Interfaces:**
- Consumes: `users-service:8000`, `books-service:8000`, `loans-service:8000` (Task 12).
- Produces: a single entry point on port 80 routing `/api/auth/*` and `/api/users/*` → `users-service`, `/api/books/*` → `books-service`, `/api/loans/*` → `loans-service`, `/` → `frontend` (wired in Task 16).

- [ ] **Step 1: Create `gateway/nginx.conf`**

```nginx
server {
    listen 80;

    location /api/auth {
        proxy_pass http://users-service:8000/auth;
        proxy_set_header Host $host;
        proxy_set_header Authorization $http_authorization;
    }

    location /api/users {
        proxy_pass http://users-service:8000/users;
        proxy_set_header Host $host;
        proxy_set_header Authorization $http_authorization;
    }

    location /api/books {
        proxy_pass http://books-service:8000/books;
        proxy_set_header Host $host;
        proxy_set_header Authorization $http_authorization;
    }

    location /api/loans {
        proxy_pass http://loans-service:8000/loans;
        proxy_set_header Host $host;
        proxy_set_header Authorization $http_authorization;
    }

    location / {
        resolver 127.0.0.11 valid=10s;
        set $frontend_upstream http://frontend:80;
        proxy_pass $frontend_upstream;
        proxy_set_header Host $host;
    }
}
```

Note: `location /`'s `proxy_pass` target is written as a variable (`$frontend_upstream`) with an explicit `resolver` directive, not a static `proxy_pass http://frontend:80;`. This matters because nginx resolves a static hostname in `proxy_pass` once, at config load time — and at this point in the plan, the `frontend` service doesn't exist yet in `docker-compose.yml` (Task 16 adds it), so there's no DNS entry for it and nginx fails to start at all (`host not found in upstream "frontend"`), taking down the already-working `/api/*` routes too. Routing the hostname through a variable forces nginx to resolve it per-request via Docker's embedded DNS server (`127.0.0.11`) instead, so a missing or not-yet-running `frontend` just means `/` 502s on request rather than crashing the whole container — and this remains correct (and arguably more robust, surviving `frontend` container restarts without an nginx reload) once Task 16 adds the `frontend` service. The four `/api/*` blocks don't need this treatment: `users-service`, `books-service`, and `loans-service` already exist as Compose service keys by this task, so their DNS names resolve fine at gateway startup.

- [ ] **Step 2: Add the `gateway` service to `docker-compose.yml`** (insert after `loans-service`, before `volumes:`)

```yaml
  gateway:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./gateway/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - users-service
      - books-service
      - loans-service
```

Note: `frontend` is referenced in `nginx.conf`'s `location /` block but the `frontend` service doesn't exist until Task 16 — the `gateway` container will log upstream errors for `/` until then, which is expected. The `/api/*` routes are independently testable now.

- [ ] **Step 3: Verify routing end-to-end**

Run:
```bash
docker compose up -d --build
sleep 5
curl -s -X POST http://localhost/api/auth/register -H "Content-Type: application/json" \
  -d '{"full_name":"Admin","email":"admin@dit.sn","password":"secret123","role":"PERSONNEL_ADMIN"}'
curl -s -X POST http://localhost/api/auth/login -H "Content-Type: application/json" \
  -d '{"email":"admin@dit.sn","password":"secret123"}'
```

Expected: the register call returns HTTP 201 with the created user; the login call returns HTTP 200 with `access_token`. This confirms the gateway correctly proxies to `users-service` through the `/api/auth` prefix rewrite.

- [ ] **Step 4: Commit**

```bash
git add gateway/ docker-compose.yml
git commit -m "feat: add nginx gateway routing /api/* to backend services"
```

---

## Task 14: Frontend — scaffold, API client, auth context, routing shell

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.jsx`
- Create: `frontend/src/App.jsx`
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/context/AuthContext.jsx`
- Create: `frontend/src/components/ProtectedRoute.jsx`
- Create: `frontend/src/components/NavBar.jsx`
- Create: `frontend/src/pages/LoginPage.jsx`
- Create: `frontend/src/pages/RegisterPage.jsx`

**Interfaces:**
- Produces: `api` (default-exported axios instance, base URL `/api`), `AuthProvider`/`useAuth()` (`{token, role, login(email, password), logout()}`), `ProtectedRoute` component, `/login` and `/register` routes.

- [ ] **Step 1: Create `package.json`**

```json
{
  "name": "bibliotheque-frontend",
  "private": true,
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.7.2",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.24.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.3.1"
  }
}
```

- [ ] **Step 2: Create `vite.config.js`**

```javascript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
});
```

- [ ] **Step 3: Create `index.html`**

```html
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <title>Bibliothèque DIT</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Create `src/api/client.js`**

```javascript
import axios from "axios";

const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

- [ ] **Step 5: Create `src/context/AuthContext.jsx`**

```jsx
import { createContext, useContext, useState } from "react";
import api from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("token"));
  const [role, setRole] = useState(localStorage.getItem("role"));

  async function login(email, password) {
    const response = await api.post("/auth/login", { email, password });
    const accessToken = response.data.access_token;
    localStorage.setItem("token", accessToken);
    setToken(accessToken);

    const me = await api.get("/users/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    localStorage.setItem("role", me.data.role);
    setRole(me.data.role);
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    setToken(null);
    setRole(null);
  }

  return (
    <AuthContext.Provider value={{ token, role, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
```

- [ ] **Step 6: Create `src/components/ProtectedRoute.jsx`**

```jsx
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, roles }) {
  const { token, role } = useAuth();
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  if (roles && !roles.includes(role)) {
    return <Navigate to="/books" replace />;
  }
  return children;
}
```

- [ ] **Step 7: Create `src/components/NavBar.jsx`**

```jsx
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function NavBar() {
  const { token, role, logout } = useAuth();

  return (
    <nav>
      <Link to="/books">Livres</Link>
      {token && <Link to="/loans">Mes emprunts</Link>}
      {role === "PERSONNEL_ADMIN" && <Link to="/users">Utilisateurs</Link>}
      {token && <Link to="/profile">Profil</Link>}
      {!token && <Link to="/login">Connexion</Link>}
      {!token && <Link to="/register">Inscription</Link>}
      {token && <button onClick={logout}>Déconnexion</button>}
    </nav>
  );
}
```

- [ ] **Step 8: Create `src/pages/LoginPage.jsx`**

```jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await login(email, password);
      navigate("/books");
    } catch (err) {
      setError("Email ou mot de passe incorrect");
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>Connexion</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input
        type="password"
        placeholder="Mot de passe"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <button type="submit">Se connecter</button>
    </form>
  );
}
```

- [ ] **Step 9: Create `src/pages/RegisterPage.jsx`**

```jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/client";

export default function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("ETUDIANT");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/auth/register", { full_name: fullName, email, password, role });
      navigate("/login");
    } catch (err) {
      setError("Impossible de créer le compte (email déjà utilisé ?)");
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <h1>Inscription</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <input placeholder="Nom complet" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input
        type="password"
        placeholder="Mot de passe"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <select value={role} onChange={(e) => setRole(e.target.value)}>
        <option value="ETUDIANT">Étudiant</option>
        <option value="PROFESSEUR">Professeur</option>
        <option value="PERSONNEL_ADMIN">Personnel administratif</option>
      </select>
      <button type="submit">Créer le compte</button>
    </form>
  );
}
```

- [ ] **Step 10: Create `src/App.jsx`** (placeholder routes for pages not built yet, to keep the app runnable)

```jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import NavBar from "./components/NavBar";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NavBar />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="*" element={<LoginPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
```

- [ ] **Step 11: Create `src/main.jsx`**

```jsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 12: Verify the app builds and runs**

Run:
```bash
cd frontend
npm install
npm run build
```

Expected: `npm run build` completes with no errors and creates a `dist/` folder. Then run `npm run dev` and open `http://localhost:5173/login` in a browser — the login form should render (API calls will fail with a network error since the gateway isn't reachable from the Vite dev server without a proxy, which is expected at this stage; full verification happens in Task 16).

- [ ] **Step 13: Commit**

```bash
git add frontend/package.json frontend/vite.config.js frontend/index.html frontend/src/
git commit -m "feat(frontend): scaffold React app with auth context and login/register pages"
```

---

## Task 15: Frontend — Books, Loans, Profile, Users pages

**Files:**
- Create: `frontend/src/pages/BooksPage.jsx`
- Create: `frontend/src/pages/LoansPage.jsx`
- Create: `frontend/src/pages/ProfilePage.jsx`
- Create: `frontend/src/pages/UsersPage.jsx`
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Consumes: `useAuth()`, `ProtectedRoute` (Task 14), gateway endpoints `/api/books`, `/api/books/search`, `/api/loans`, `/api/loans/{id}/return`, `/api/users`, `/api/users/me`.

- [ ] **Step 1: Create `src/pages/BooksPage.jsx`**

```jsx
import { useEffect, useState } from "react";
import api from "../api/client";
import { useAuth } from "../context/AuthContext";

const emptyForm = { title: "", author: "", isbn: "", total_copies: 1 };

export default function BooksPage() {
  const { role } = useAuth();
  const [books, setBooks] = useState([]);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");

  async function loadBooks(query = "") {
    const url = query ? `/books/search?title=${encodeURIComponent(query)}` : "/books";
    const response = await api.get(url);
    setBooks(response.data);
  }

  useEffect(() => {
    loadBooks();
  }, []);

  async function handleSearch(e) {
    e.preventDefault();
    loadBooks(search);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    try {
      if (editingId) {
        await api.put(`/books/${editingId}`, form);
      } else {
        await api.post("/books", form);
      }
      setForm(emptyForm);
      setEditingId(null);
      loadBooks();
    } catch (err) {
      setError("Opération impossible (ISBN déjà utilisé ?)");
    }
  }

  function startEdit(book) {
    setEditingId(book.id);
    setForm({ title: book.title, author: book.author, isbn: book.isbn, total_copies: book.total_copies });
  }

  async function handleDelete(id) {
    await api.delete(`/books/${id}`);
    loadBooks();
  }

  async function handleBorrow(id) {
    setError("");
    try {
      await api.post("/loans", { book_id: id });
      loadBooks();
    } catch (err) {
      setError("Emprunt impossible (livre indisponible ?)");
    }
  }

  return (
    <div>
      <h1>Livres</h1>
      {error && <p style={{ color: "red" }}>{error}</p>}
      <form onSubmit={handleSearch}>
        <input placeholder="Rechercher par titre" value={search} onChange={(e) => setSearch(e.target.value)} />
        <button type="submit">Rechercher</button>
      </form>

      {role === "PERSONNEL_ADMIN" && (
        <form onSubmit={handleSubmit}>
          <h2>{editingId ? "Modifier le livre" : "Ajouter un livre"}</h2>
          <input
            placeholder="Titre"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
          <input
            placeholder="Auteur"
            value={form.author}
            onChange={(e) => setForm({ ...form, author: e.target.value })}
            required
          />
          <input
            placeholder="ISBN"
            value={form.isbn}
            onChange={(e) => setForm({ ...form, isbn: e.target.value })}
            required
          />
          <input
            type="number"
            min="1"
            value={form.total_copies}
            onChange={(e) => setForm({ ...form, total_copies: Number(e.target.value) })}
            required
          />
          <button type="submit">{editingId ? "Enregistrer" : "Ajouter"}</button>
        </form>
      )}

      <ul>
        {books.map((book) => (
          <li key={book.id}>
            <strong>{book.title}</strong> — {book.author} ({book.isbn}) — {book.available_copies}/
            {book.total_copies} dispo
            <button onClick={() => handleBorrow(book.id)} disabled={book.available_copies < 1}>
              Emprunter
            </button>
            {role === "PERSONNEL_ADMIN" && (
              <>
                <button onClick={() => startEdit(book)}>Modifier</button>
                <button onClick={() => handleDelete(book.id)}>Supprimer</button>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Create `src/pages/LoansPage.jsx`**

```jsx
import { useEffect, useState } from "react";
import api from "../api/client";

export default function LoansPage() {
  const [loans, setLoans] = useState([]);

  async function loadLoans() {
    const response = await api.get("/loans");
    setLoans(response.data);
  }

  useEffect(() => {
    loadLoans();
  }, []);

  async function handleReturn(id) {
    await api.patch(`/loans/${id}/return`);
    loadLoans();
  }

  return (
    <div>
      <h1>Mes emprunts</h1>
      <ul>
        {loans.map((loan) => (
          <li key={loan.id}>
            Livre #{loan.book_id} — emprunté le {new Date(loan.borrowed_at).toLocaleDateString()} — statut :{" "}
            {loan.status}
            {loan.status === "EN_COURS" && <button onClick={() => handleReturn(loan.id)}>Retourner</button>}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Create `src/pages/ProfilePage.jsx`**

```jsx
import { useEffect, useState } from "react";
import api from "../api/client";

export default function ProfilePage() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    api.get("/users/me").then((response) => setUser(response.data));
  }, []);

  if (!user) return <p>Chargement...</p>;

  return (
    <div>
      <h1>Mon profil</h1>
      <p>Nom : {user.full_name}</p>
      <p>Email : {user.email}</p>
      <p>Rôle : {user.role}</p>
    </div>
  );
}
```

- [ ] **Step 4: Create `src/pages/UsersPage.jsx`**

```jsx
import { useEffect, useState } from "react";
import api from "../api/client";

export default function UsersPage() {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    api.get("/users").then((response) => setUsers(response.data));
  }, []);

  return (
    <div>
      <h1>Utilisateurs</h1>
      <ul>
        {users.map((user) => (
          <li key={user.id}>
            {user.full_name} — {user.email} — {user.role}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 5: Update `src/App.jsx`** (replace the whole file)

```jsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import NavBar from "./components/NavBar";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import BooksPage from "./pages/BooksPage";
import LoansPage from "./pages/LoansPage";
import ProfilePage from "./pages/ProfilePage";
import UsersPage from "./pages/UsersPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <NavBar />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/books"
            element={
              <ProtectedRoute>
                <BooksPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/loans"
            element={
              <ProtectedRoute>
                <LoansPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute roles={["PERSONNEL_ADMIN"]}>
                <UsersPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<LoginPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
```

- [ ] **Step 6: Verify the app builds**

Run: `cd frontend && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): add books, loans, profile, and users pages"
```

---

## Task 16: Frontend Dockerfile and full-stack wiring

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Modify: `docker-compose.yml`

**Interfaces:**
- Produces: a `frontend` container serving the built React app on port 80, wired into `docker-compose.yml` and reachable through the `gateway`'s `location /` block (Task 13).

- [ ] **Step 1: Create `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri /index.html;
    }
}
```

- [ ] **Step 2: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

Note: `frontend/nginx.conf` overrides the stock `nginx:alpine` default config with `try_files $uri /index.html;`. This is required because the app uses React Router's `BrowserRouter`, which relies on client-side JavaScript to render a route like `/login` — but a browser (or `curl`) requesting `/login` directly sends that literal path to nginx first. Without the fallback, nginx looks for a file at `/login` on disk, doesn't find one, and returns a bare 404 instead of serving `index.html` (which is what actually boots the React app and lets the router take over). `try_files` serves the matched static asset if one exists (JS/CSS bundles, favicon, etc.) and falls back to `index.html` for everything else, which is the standard pattern for any client-side-routed SPA served by a static file server.

- [ ] **Step 3: Add the `frontend` service to `docker-compose.yml`** (insert after `loans-service`, before `gateway`)

```yaml
  frontend:
    build: ./frontend
```

- [ ] **Step 4: Make `gateway` depend on `frontend`** (in the existing `gateway` service block, update `depends_on`)

```yaml
  gateway:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./gateway/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - frontend
      - users-service
      - books-service
      - loans-service
```

- [ ] **Step 5: Full-stack verification**

Run:
```bash
docker compose up -d --build
sleep 5
```

If you have a browser available, open `http://localhost/register`: create a `PERSONNEL_ADMIN` account, log in at `http://localhost/login`, add a book on `http://localhost/books`, borrow it, then check `http://localhost/loans` shows the loan and `http://localhost/users` (as admin) lists the account. This is the golden-path walkthrough required before considering the stack complete.

If no browser/display is available (e.g. a headless CI/agent environment), perform the equivalent verification by driving the same HTTP calls the frontend's JS would make, through the gateway on port 80: `POST /api/auth/register` (PERSONNEL_ADMIN), `POST /api/auth/login`, `POST /api/books` with the admin JWT, `POST /api/loans` to borrow it, `GET /api/loans` to confirm it shows up, `PATCH /api/loans/{id}/return`, and `GET /api/users` (as admin) to confirm the account is listed. Also curl `http://localhost/`, `http://localhost/login`, and `http://localhost/register` directly and confirm each returns `200` with the built `index.html` (not a 404) — this is what `frontend/nginx.conf`'s `try_files` fallback exists to guarantee.

- [ ] **Step 6: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf docker-compose.yml
git commit -m "feat(frontend): add Dockerfile and wire into docker-compose"
```

---

## Task 17: Jenkins — containerized Jenkins with Docker access, Jenkinsfile

**Files:**
- Create: `jenkins/Dockerfile`
- Modify: `docker-compose.yml`
- Create: `Jenkinsfile`

**Interfaces:**
- Produces: a `jenkins` service in Compose with Docker CLI installed, and a repo-root `Jenkinsfile` with stages `Checkout → Build & Test → Build Docker Images → Deploy`.

- [ ] **Step 1: Create `jenkins/Dockerfile`**

```dockerfile
FROM jenkins/jenkins:lts

USER root

RUN apt-get update && \
    apt-get install -y ca-certificates curl gnupg && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y docker-ce-cli docker-compose-plugin && \
    rm -rf /var/lib/apt/lists/*

USER jenkins
```

- [ ] **Step 2: Add the `jenkins` service to `docker-compose.yml`** (insert after `gateway`, before `volumes:`)

```yaml
  jenkins:
    build: ./jenkins
    ports:
      - "8080:8080"
    volumes:
      - jenkins_home:/var/jenkins_home
      - /var/run/docker.sock:/var/run/docker.sock
```

Also add `jenkins_home:` to the `volumes:` block at the bottom of the file, alongside `users_db_data`, `books_db_data`, `loans_db_data`.

Note: on the host machine, the `jenkins` user inside the container must be able to write to the mounted `/var/run/docker.sock`. If `docker compose up jenkins` logs permission errors when the pipeline runs `docker` commands, find the host's docker group id with `getent group docker` and add `group_add: ["<that gid>"]` to the `jenkins` service.

- [ ] **Step 3: Create the repo-root `Jenkinsfile`**

```groovy
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build & Test') {
            steps {
                sh '''
                    for service in users-service books-service loans-service; do
                        echo "Testing $service"
                        cd $service
                        python3 -m venv .venv
                        . .venv/bin/activate
                        pip install -r requirements.txt
                        pytest tests/ -v
                        deactivate
                        cd ..
                    done
                '''
            }
        }

        stage('Build Docker Images') {
            steps {
                sh 'docker compose build'
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker compose down'
                sh 'docker compose up -d'
            }
        }
    }
}
```

- [ ] **Step 4: Verify Jenkins boots and can reach Docker**

Run:
```bash
docker compose up -d --build jenkins
sleep 10
docker compose exec jenkins docker ps
```

Expected: `docker ps` inside the `jenkins` container lists the host's running containers (proving the mounted socket works) without a permission error. If it fails with `permission denied`, apply the `group_add` fix noted in Step 2.

Then open `http://localhost:8080` in a browser, complete the Jenkins setup wizard (the initial admin password is in `docker compose logs jenkins`, or `docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword`), create a Pipeline job pointing at this repository's `Jenkinsfile`, and run it once to confirm all four stages go green.

- [ ] **Step 5: Commit**

```bash
git add jenkins/ docker-compose.yml Jenkinsfile
git commit -m "feat: add Jenkins service and Jenkinsfile pipeline"
```

---

## Task 18: README

**Files:**
- Create: `README.md`

**Interfaces:**
- Produces: the project's top-level documentation, satisfying the exam's README deliverable (installation, Docker Compose usage, Jenkins pipeline, project structure).

- [ ] **Step 1: Create `README.md`**

```markdown
# Bibliothèque Numérique Microservices

Plateforme de gestion de bibliothèque pour le DIT, basée sur une architecture microservices (FastAPI + PostgreSQL), un frontend React, une passerelle Nginx, et un pipeline CI/CD Jenkins.

## Architecture

- `users-service` (FastAPI, port interne 8000) — comptes utilisateurs, rôles (`ETUDIANT`, `PROFESSEUR`, `PERSONNEL_ADMIN`), authentification JWT. DB : `users-db` (PostgreSQL).
- `books-service` (FastAPI, port interne 8000) — CRUD livres, recherche, gestion des exemplaires disponibles. DB : `books-db` (PostgreSQL).
- `loans-service` (FastAPI, port interne 8000) — emprunts/retours, historique. Appelle `books-service` en interne. DB : `loans-db` (PostgreSQL).
- `frontend` (React + Vite, servi par Nginx) — interface utilisateur.
- `gateway` (Nginx) — point d'entrée unique sur le port 80, route `/api/auth`, `/api/users`, `/api/books`, `/api/loans` vers le microservice correspondant et `/` vers le frontend.
- `jenkins` — pipeline CI/CD (voir plus bas).

## Installation

Prérequis : Docker et Docker Compose.

```bash
git clone <url-du-repo>
cd Examen_Container_Visualisation
```

## Lancement avec Docker Compose

```bash
docker compose up -d --build
```

- Application : http://localhost
- Jenkins : http://localhost:8080

Pour arrêter et supprimer les conteneurs (en gardant les données) :

```bash
docker compose down
```

Pour tout supprimer y compris les volumes de bases de données :

```bash
docker compose down -v
```

## Comptes et rôles

Créez un compte via `http://localhost/register`. Le rôle `PERSONNEL_ADMIN` donne accès à la gestion des livres et à la liste des utilisateurs ; les rôles `ETUDIANT` et `PROFESSEUR` peuvent emprunter/retourner des livres et consulter leur propre historique.

## Fonctionnement du pipeline Jenkins

Le `Jenkinsfile` définit 4 étapes exécutées dans le conteneur `jenkins` (qui a accès au Docker de l'hôte via `/var/run/docker.sock`) :

1. **Checkout** — récupère le code depuis GitHub.
2. **Build & Test** — installe les dépendances Python de chaque microservice et exécute `pytest`.
3. **Build Docker Images** — `docker compose build`.
4. **Deploy** — `docker compose down && docker compose up -d`.

Pour configurer Jenkins la première fois : ouvrez `http://localhost:8080`, récupérez le mot de passe initial avec `docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword`, terminez l'assistant d'installation, puis créez un job de type "Pipeline" pointant vers ce dépôt Git et son `Jenkinsfile`.

## Structure du projet

```
.
├── users-service/       # Microservice utilisateurs + authentification
├── books-service/       # Microservice livres
├── loans-service/       # Microservice emprunts
├── frontend/             # Application React
├── gateway/              # Configuration Nginx (reverse proxy)
├── jenkins/              # Image Jenkins avec Docker CLI
├── docker-compose.yml    # Orchestration de tous les services
├── Jenkinsfile           # Pipeline CI/CD
└── docs/                 # Spécification, plan, captures d'écran
```

## Tests

Chaque microservice a sa propre suite de tests `pytest` (base SQLite en mémoire, aucune dépendance à Postgres) :

```bash
cd users-service   # ou books-service / loans-service
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with installation and pipeline instructions"
```

---

## Final Verification Checklist

After Task 18, confirm the whole exam deliverable list is satisfied:

- [ ] `docker compose up -d --build` brings up all 9 services with no crash-looping containers (`docker compose ps` shows all `Up`).
- [ ] Registering, logging in, adding a book, borrowing it, and returning it all work through the browser at `http://localhost`.
- [ ] `PERSONNEL_ADMIN` can see `/users` and `/books` management forms; `ETUDIANT`/`PROFESSEUR` cannot.
- [ ] Each of `users-service`, `books-service`, `loans-service` has a passing `pytest tests/` run and its own `Dockerfile`.
- [ ] `frontend` has its own `Dockerfile`.
- [ ] `docker-compose.yml` and `Jenkinsfile` exist at the repo root.
- [ ] A Jenkins pipeline run (triggered manually through the UI per Task 17 Step 4) completes all 4 stages successfully.
- [ ] `README.md` covers installation, Docker Compose usage, the Jenkins pipeline, and project structure.
- [ ] Take the screenshots needed for the PDF report (registration, login, books list, borrow/return, Jenkins pipeline green run) — this is a manual step for the report, not automatable.
