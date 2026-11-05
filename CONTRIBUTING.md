# Contributing to UPI Without Internet

Thank you for your interest in contributing to the **UPI Without Internet** academic simulation project! This project demonstrates offline mesh networking, cryptographic packet routing, idempotency deduplication, and deferred ledger reconciliation.

---

## 1. Code of Conduct

We are committed to providing a welcoming, inclusive, and harassment-free environment for everyone. Please be respectful, constructive, and collaborative in all communications.

---

## 2. Academic Project Scope & Disclaimer

> **IMPORTANT**: This repository is an **educational research simulation** designed for computer engineering demonstrations, academic viva examinations, and fintech architecture study. It does **not** connect to real NPCI infrastructure, execute real bank account transfers, or handle real fiat currency. Contributions must preserve this academic boundary and never claim real-money transactions.

---

## 3. Getting Started

### Fork and Clone
1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/perryvegehan/UPI_Without_Internet.git
   cd UPI_Without_Internet
   ```

### Prerequisites
- **Python**: Version 3.11 or higher
- **Node.js**: Version 18.0.0 or higher
- **Package Managers**: `pip` and `npm`

---

## 4. Development Workflow

### Setting up Backend (Python / Flask)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```
The Flask backend runs on `http://127.0.0.1:5001`.

### Setting up Frontend (React / TypeScript / Vite)
```bash
cd frontend
npm install
npm run dev
```
The Vite development server runs on `http://localhost:3000` with automated reverse-proxying of `/api` and `/auth` routes to Flask.

---

## 5. Coding Standards

### Python (Backend)
- Follow **PEP 8** style guidelines.
- Use **snake_case** for module, function, and variable names.
- Use **PascalCase** for classes and SQLAlchemy models.
- Include explicit type annotations (`typing` module) for public service methods.
- Document cryptographic routines with RFC references (RSA-OAEP, AES-256-GCM, SHA-256).

### TypeScript & React (Frontend)
- Use **TypeScript** strictly without implicit `any`.
- Name React components using **PascalCase** (e.g., `MeshVisualizer.tsx`).
- Name utility modules using **camelCase** (e.g., `formatters.ts`, `qr.ts`).
- Ensure all styling uses **Tailwind CSS** utility classes; avoid inline styles.

---

## 6. Testing & Quality Assurance

Before opening a pull request, ensure all test suites pass with zero failures:

### Run Complete Test Suite
From the repository root:
```bash
npm run test:all
```

### Run Python Tests Only
```bash
pytest backend/tests
```

### Run Frontend Unit Tests Only
```bash
npm test
```

### TypeScript Validation
```bash
npm run lint
```

---

## 7. Submitting a Pull Request

1. Create a feature branch with a descriptive name:
   ```bash
   git checkout -b feature/improved-mesh-routing
   ```
2. Write clean, self-documenting code with unit tests covering new logic.
3. Commit your changes with conventional commit messages:
   ```bash
   git commit -m "feat(mesh): add adaptive retry backoff for lossy links"
   ```
4. Push to your fork and submit a Pull Request to `main`.
5. Provide a clear PR description explaining the changes, rationale, and test results.
