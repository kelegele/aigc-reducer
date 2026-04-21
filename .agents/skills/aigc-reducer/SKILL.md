```markdown
# aigc-reducer Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill provides a comprehensive guide to the development patterns, coding conventions, and workflows used in the `aigc-reducer` repository. The project is primarily Python-based, with a React frontend, and focuses on backend service development, API endpoint management, ORM modeling, and frontend component creation. This guide will help you contribute efficiently and consistently to the codebase.

## Coding Conventions

- **File Naming:**  
  Use camelCase for file names.  
  _Example:_  
  ```
  creditAccount.py
  testAuthService.py
  ```

- **Import Style:**  
  Use relative imports within modules.  
  _Example:_  
  ```python
  from .models import User
  from ..services.auth import authenticate_user
  ```

- **Export Style:**  
  Use default exports (Python's standard module exports).  
  _Example:_  
  ```python
  # In auth.py
  def authenticate_user(...):
      ...
  ```

- **Commit Messages:**  
  Follow [Conventional Commits](https://www.conventionalcommits.org/) with prefixes like `feat` and `fix`.  
  _Example:_  
  ```
  feat: add SMS service for user notifications
  fix: correct token expiration logic in auth service
  ```

## Workflows

### Add Backend Service or Feature
**Trigger:** When you need to implement a new backend service (e.g., auth, token, SMS) or feature.  
**Command:** `/new-service`

1. Create or update a service file in `web/src/aigc_web/services/` (e.g., `auth.py`, `sms.py`, `token.py`).
2. Create or update the corresponding test file in `web/tests/` (e.g., `test_auth_service.py`, `test_sms.py`, `test_token.py`).

_Example:_
```python
# web/src/aigc_web/services/sms.py
def send_sms(phone_number: str, message: str) -> bool:
    # Implementation here
    return True
```
```python
# web/tests/test_sms.py
from aigc_web.services.sms import send_sms

def test_send_sms():
    assert send_sms("+1234567890", "Hello!") is True
```

---

### Add API Endpoint with Tests
**Trigger:** When you want to expose a new API endpoint (e.g., auth routes).  
**Command:** `/new-api-endpoint`

1. Create or update a router file in `web/src/aigc_web/routers/` (e.g., `auth.py`).
2. Update `web/src/aigc_web/main.py` to include the new router if needed.
3. Add or update a test file in `web/tests/` (e.g., `test_auth_router.py`).

_Example:_
```python
# web/src/aigc_web/routers/auth.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/login")
def login(...):
    ...
```
```python
# web/src/aigc_web/main.py
from .routers import auth
app.include_router(auth.router)
```
```python
# web/tests/test_auth_router.py
def test_login(client):
    response = client.post("/login", json={...})
    assert response.status_code == 200
```

---

### Add ORM Model and Tests
**Trigger:** When you need to add a new database model/table.  
**Command:** `/new-model`

1. Create or update a model file in `web/src/aigc_web/models/` (e.g., `user.py`, `credit_account.py`).
2. Add or update test files for models in `web/tests/` (e.g., `test_models.py`).
3. Update Alembic migration files or setup if needed.

_Example:_
```python
# web/src/aigc_web/models/user.py
from sqlalchemy import Column, Integer, String
from .base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
```
```python
# web/tests/test_models.py
from aigc_web.models.user import User

def test_user_model():
    user = User(name="Alice")
    assert user.name == "Alice"
```
```bash
# Alembic migration (example)
alembic revision --autogenerate -m "add user model"
```

---

### Add Frontend Page or Component
**Trigger:** When you want to add a new page or component to the React frontend.  
**Command:** `/new-frontend-page`

1. Create a new file in `web/frontend/src/pages/` or `web/frontend/src/components/` (e.g., `Login.tsx`, `Credits.tsx`).
2. Update `web/frontend/src/App.tsx` and/or `web/frontend/src/main.tsx` for routing/layout.
3. Optionally update styles or configuration.

_Example:_
```tsx
// web/frontend/src/pages/Login.tsx
import React from "react";

export default function Login() {
  return <div>Login Page</div>;
}
```
```tsx
// web/frontend/src/App.tsx
import Login from "./pages/Login";
// Add <Route path="/login" element={<Login />} /> as needed
```

## Testing Patterns

- **Framework:** Unknown (likely pytest for Python, React Testing Library or Jest for frontend)
- **File Pattern:**  
  - Backend: `web/tests/test_*.py`
  - Frontend: `*.test.ts`
- **Example Backend Test:**
  ```python
  # web/tests/test_token.py
  def test_generate_token():
      ...
  ```
- **Example Frontend Test:**
  ```typescript
  // Login.test.ts
  import { render } from "@testing-library/react";
  import Login from "./Login";

  test("renders login page", () => {
    render(<Login />);
    // assertions here
  });
  ```

## Commands

| Command              | Purpose                                                      |
|----------------------|--------------------------------------------------------------|
| /new-service         | Scaffold a new backend service and its test                  |
| /new-api-endpoint    | Add a new API endpoint with router logic and integration test|
| /new-model           | Add a new ORM model and related tests/migrations             |
| /new-frontend-page   | Create a new frontend page or component                      |
```
