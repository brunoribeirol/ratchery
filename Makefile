.PHONY: test compile lint unit integration manifest verify release-smoke shellcheck clean

# Runs the portable CI gates. GitHub's Linux legs additionally run the optional
# `make shellcheck` gate because ShellCheck is preinstalled there; contributors
# editing shell code should install it and run that target locally too.
test: compile lint integration unit verify

compile:
	python3 -m py_compile lib/*.py
	bash -n install.sh bin/ratchery bin/agent-workspace tests/run-tests.sh

# Requires ruff installed (pip install ruff==0.6.2, matching ci.yml's pin) --
# not a project dependency (stdlib-only), a dev-tool contributors need locally.
lint:
	ruff check lib/ scripts/ tests/ bin/

integration:
	bash tests/run-tests.sh

unit:
	python3 -m unittest discover -s tests -p 'test_*.py'

manifest:
	python3 scripts/gen-manifest.py

verify:
	python3 scripts/verify-manifest.py
	python3 scripts/verify-action-pins.py
	python3 scripts/verify-doc-links.py

# Release-only gate: build the manifest-backed archive, install that exact
# artifact under an isolated HOME/prefix, initialize a fixture, and run doctor.
release-smoke:
	@set -e; release_dir=$$(mktemp -d); \
	trap 'rm -rf "$$release_dir"' EXIT; \
	python3 scripts/build-release.py --output-dir "$$release_dir" >/dev/null; \
	python3 scripts/smoke-test-release.py "$$release_dir"/*.tar.gz

# Not part of `test` because ShellCheck is not a runtime/dev dependency on every
# supported host. It is blocking on GitHub's Linux CI legs and should be run
# locally before touching any listed shell file.
shellcheck:
	shellcheck install.sh bin/ratchery bin/agent-workspace tests/run-tests.sh

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
