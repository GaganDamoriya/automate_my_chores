.PHONY: seed api web install install-api install-web install-agents

# One venv for everything (create once, then `source .venv/bin/activate`):
#   python3 -m venv .venv && source .venv/bin/activate
# (If you already use .venv-adk, just activate that and run the install-* targets.)

install: install-api install-agents install-web   ## install everything into the ACTIVE venv (+ web node_modules)

install-api:        ## backend web server deps -> active venv
	pip install -r api/requirements.txt

install-agents:     ## Gemini/ADK deps -> active venv
	pip install -r agents/requirements.txt

install-web:        ## frontend deps
	cd web && npm install

seed:               ## generate simulated activity data
	python3 seed/generate.py

api:                ## run FastAPI (uses whatever venv is active)
	cd api && uvicorn app.main:app --reload --port 8000

web:                ## run Next.js dev server
	cd web && npm run dev
