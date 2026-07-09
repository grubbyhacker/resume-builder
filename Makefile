.PHONY: validate render render-markdown docx pdf check check-markdown check-docx check-tika check-urls check-office clean

validate:
	mise exec -- uv run python scripts/validate_yaml.py

render: render-markdown docx

render-markdown: validate
	mise exec -- uv run python scripts/render_markdown.py

docx: validate
	mise exec -- uv run python scripts/render_docx.py

pdf: docx
	mise exec -- uv run python scripts/build_pdf.py

check: render check-markdown check-docx check-tika

check-markdown:
	mise exec -- uv run python scripts/check_parse.py

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
