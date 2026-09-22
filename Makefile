.PHONY: setup run clean

VENV := venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

setup:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@if [ ! -d models ]; then $(PY) core/download_paddle_models.py; fi
	@echo "الإعداد اكتمل. شغّل: make run"

run:
	$(VENV)/bin/uvicorn api:app --host 0.0.0.0 --port 8000 --reload

clean:
	rm -rf $(VENV) __pycache__ */__pycache__
