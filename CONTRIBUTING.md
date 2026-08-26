# Contributing to FixItFixa

Thank you for your interest in contributing to **FixItFixa**! This document provides guidelines and workflows for developers, contributors, and maintainers.

---

## 1. Code of Conduct & Principles

* **Clean Architecture**: Preserve the 4-layer separation (Presentation UI → Business Services → OS/System → Configuration/Common).
* **Defensive Programming**: Explicit exception handling, no silent exception swallowing, input validation at boundaries.
* **Full Typing**: Use Python 3.10+ type hints, `TypedDict`, and `dataclasses`. Run `mypy` before submitting PRs.
* **100% Test Quality**: All new features, services, or bug fixes must include unit/integration tests with `pytest`.

---

## 2. Development Setup

### Prerequisites
* Python 3.10 or higher
* Git

### Local Installation
```bash
# 1. Clone the repository
git clone https://github.com/stargate91/discord-bot-manager.git
cd fixitfixa

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux / macOS
# or
.venv\Scripts\activate     # Windows

# 3. Install production and development dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov mypy ruff
```

---

## 3. Running Tests & Quality Checks

Run the automated test suite with coverage reporting:
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_service_container.py -v

# Run type checker
mypy core bot
```

---

## 4. Git Workflow & Branching Strategy

* `main`: Production-ready, stable releases.
* `feature/<feature-name>`: New capabilities or architectural improvements.
* `fix/<bug-name>`: Targeted bug fixes.
* `refactor/<scope>`: Code quality improvements without functional changes.

### Commit Conventions
Follow standard [Conventional Commits](https://www.conventionalcommits.org/):
* `feat: add Prometheus metrics exporter`
* `fix: prevent race condition in StateRepository during concurrent saves`
* `docs: update configuration schema in README.md`
* `test: add unit tests for cross-platform path normalization`

---

## 5. Pull Request Guidelines

1. Ensure all **pytest unit and integration tests pass (100% green)**.
2. Verify that **test coverage remains at or above 85%**.
3. Include clear docstrings for all public classes and functions.
4. Update `CHANGELOG.md` with relevant notes under the `[Unreleased]` section.
