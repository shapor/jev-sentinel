.PHONY: hunt bench serve victim check

hunt:     ## score every Swarm Traces unit (resumable)
	python3 hunt.py swarm

bench:    ## score sanctioned CTF agent actions (the false-positive set)
	python3 hunt.py cybench

serve:    ## demo page + API on http://127.0.0.1:8000
	python3 server.py

victim:   ## local vulnerable target for the live agent on http://127.0.0.1:8080
	cd victim && python3 app.py

check:    ## judge one action: make check A='ls -la'
	python3 sentinel.py "$(A)"
