# MorphoLapse build & test targets.
#
# Usage:
#   make install        # install runtime + dev deps in the current Python
#   make lint           # ruff check + format check
#   make format         # ruff check --fix + ruff format (apply)
#   make typecheck      # mypy on src/
#   make test           # full pytest suite
#   make test-fast      # exclude slow markers
#   make bench          # perf tests only
#   make cov            # pytest with coverage HTML report
#   make build-debug    # PyInstaller debug profile
#   make build-release  # PyInstaller release profile
#   make build-all      # both
#   make clean          # remove build/ dist/ *.spec __pycache__/ .pytest_cache/ .ruff_cache/ .mypy_cache/
#   make all            # lint + test + build-all
#
# Tested with GNU Make 4 on Windows (Git Bash / MSYS2) and Linux.

PYTHON ?= python
PIP    ?= $(PYTHON) -m pip

.PHONY: install lint format typecheck test test-fast bench cov \
        build-debug build-release build-all clean all help

help:
	@echo "Targets: install lint format typecheck test test-fast bench cov build-debug build-release build-all clean all"

install:
	$(PIP) install -e ".[dev]"

lint:
	$(PYTHON) -m ruff check . --select=E,F,W,B,S
	$(PYTHON) -m ruff format --check .

format:
	$(PYTHON) -m ruff check . --fix
	$(PYTHON) -m ruff format .

typecheck:
	$(PYTHON) -m mypy src --ignore-missing-imports

test:
	$(PYTHON) -m pytest tests/ -q

test-fast:
	$(PYTHON) -m pytest tests/ -q -m "not slow"

bench:
	$(PYTHON) -m pytest tests/perf -q -v

cov:
	$(PYTHON) -m pytest tests/ -q --cov=src --cov-report=term-missing --cov-report=html:tests/runs/coverage

build-debug:
	$(PYTHON) build.py debug

build-release:
	$(PYTHON) build.py release

build-all:
	$(PYTHON) build.py all

clean:
	$(PYTHON) build.py clean
	@$(PYTHON) -c "import shutil, glob, os; \
		[shutil.rmtree(p, ignore_errors=True) for p in ['build', 'dist', '.pytest_cache', '.ruff_cache', '.mypy_cache']]; \
		[shutil.rmtree(p, ignore_errors=True) for p in glob.glob('**/__pycache__', recursive=True)]; \
		[os.remove(p) for p in glob.glob('*.spec') if os.path.exists(p)]; \
		print('Cleaned.')"

all: lint test build-all
