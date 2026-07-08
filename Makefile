.PHONY: validate render check clean

validate:
	mise exec -- uv run python scripts/validate_yaml.py

render: validate
	mise exec -- uv run python scripts/render_markdown.py

check: render
	mise exec -- uv run python scripts/check_parse.py

clean:
	rm -rf output
