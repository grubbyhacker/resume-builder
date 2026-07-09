.PHONY: validate render render-markdown render-structured docx pdf check check-markdown check-structured check-docx check-tika check-urls check-office clean

validate:
	mise exec -- uv run python scripts/validate_yaml.py

render: render-markdown render-structured docx

render-markdown: validate
	mise exec -- uv run python scripts/render_markdown.py

render-structured: validate
	mise exec -- uv run python scripts/render_structured_markdown.py

docx: validate
	mise exec -- uv run python scripts/render_docx.py

pdf: docx
	mise exec -- uv run python scripts/build_pdf.py

check: render check-markdown check-structured check-docx check-tika

check-markdown:
	mise exec -- uv run python scripts/check_parse.py

check-structured:
	mise exec -- uv run python scripts/check_structured_markdown.py

check-docx:
	mise exec -- uv run python scripts/check_docx.py

check-tika:
	scripts/check_tika_docker.sh

check-urls:
	mise exec -- uv run python scripts/check_urls.py

check-office: pdf
	mise exec -- uv run python scripts/check_office.py

clean:
	rm -rf output
