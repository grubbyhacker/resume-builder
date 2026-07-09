.PHONY: validate render render-markdown render-structured docx pdf check check-markdown check-structured check-docx check-tika check-urls check-office clean

RESUME ?= resume.yaml

validate:
	mise exec -- uv run python scripts/validate_yaml.py --resume "$(RESUME)"

render: render-markdown render-structured docx

render-markdown: validate
	mise exec -- uv run python scripts/render_markdown.py --resume "$(RESUME)"

render-structured: validate
	mise exec -- uv run python scripts/render_structured_markdown.py --resume "$(RESUME)"

docx: validate
	mise exec -- uv run python scripts/render_docx.py --resume "$(RESUME)"

pdf: docx
	mise exec -- uv run python scripts/build_pdf.py --resume "$(RESUME)"

check: render check-markdown check-structured check-docx check-tika

check-markdown:
	mise exec -- uv run python scripts/check_parse.py --resume "$(RESUME)"

check-structured:
	mise exec -- uv run python scripts/check_structured_markdown.py --resume "$(RESUME)"

check-docx:
	mise exec -- uv run python scripts/check_docx.py --resume "$(RESUME)"

check-tika:
	RESUME="$(RESUME)" scripts/check_tika_docker.sh

check-urls:
	mise exec -- uv run python scripts/check_urls.py --resume "$(RESUME)"

check-office: pdf
	mise exec -- uv run python scripts/check_office.py --resume "$(RESUME)"

clean:
	rm -rf output
