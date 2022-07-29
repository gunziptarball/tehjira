SHELL=bash

.git/hooks/pre-commit:.pre-commit-config.yaml
	if ! command -v pre-commit >/dev/null 2>&1; then \
		echo "Please install pre-commit!"; \
		exit 1; \
	fi; \
	pre-commit install;

pre-commit: .git/hooks/pre-commit

pretty: pre-commit
	pre-commit run --all-files; echo
