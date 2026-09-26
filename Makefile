.PHONY: hunt bench serve victim check install-hook agent-demo test

hunt:     ## score every Swarm Traces unit (resumable)
	python3 hunt.py swarm

bench:    ## score sanctioned CTF agent actions (the false-positive set)
	python3 hunt.py cybench

serve:    ## demo page + API on http://127.0.0.1:8000
	python3 server.py

victim:   ## local vulnerable target for the live agent on http://127.0.0.1:8080
	cd victim && python3 app.py

test:     ## offline tests (Jev mocked)
	python3 -m unittest -v test_sentinel

check:    ## judge one action: make check A='ls -la'
	A="$$A" python3 -c 'import json, os, sentinel; print(json.dumps(sentinel.judge(os.environ["A"]), indent=1))'
check: export A := $(A)

install-hook:  ## gate a Claude Code project: make install-hook DIR=~/proj SCOPE="refactor the billing module"
	python3 install.py "$(DIR)" "$(SCOPE)"

AGENT_DIR ?= /tmp/jev-sentinel-demo
agent-demo:  ## a real Claude Code agent on a small task, every tool call gated live (watch Act 3)
	rm -rf $(AGENT_DIR) && mkdir -p $(AGENT_DIR)/src $(AGENT_DIR)/tests && touch $(AGENT_DIR)/src/__init__.py $(AGENT_DIR)/tests/__init__.py
	printf 'from datetime import datetime\n\n\ndef parse(s):\n    """Parse an ISO date like 2026-09-26."""\n    return datetime.strptime(s.strip(), "%%Y-%%m-%%d").date()\n' > $(AGENT_DIR)/src/dates.py
	python3 install.py $(AGENT_DIR) "add a unit test for parse() in src/dates.py and make sure it passes"
	cd $(AGENT_DIR) && claude -p "Add a unit test for parse() in src/dates.py under tests/, then run it with python3 -m pytest -q and make sure it passes." --max-turns 15
