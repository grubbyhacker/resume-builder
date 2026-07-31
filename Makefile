.PHONY: validate render render-markdown render-structured docx pdf render-release check check-unit check-markdown check-structured check-docx check-tika check-urls check-office clean _render _render-markdown _render-structured _docx _pdf

RESUME ?= resume.yaml
PYTHON_RUN ?= mise exec -- uv run

validate:
	$(PYTHON_RUN) python scripts/validate_yaml.py --resume "$(RESUME)"

render:
	$(MAKE) clean
	$(MAKE) _render

_render: _render-markdown _render-structured _docx

render-markdown:
	$(MAKE) clean
	$(MAKE) _render-markdown

_render-markdown: validate
	$(PYTHON_RUN) python scripts/render_markdown.py --resume "$(RESUME)"

render-structured:
	$(MAKE) clean
	$(MAKE) _render-structured

_render-structured: validate
	$(PYTHON_RUN) python scripts/render_structured_markdown.py --resume "$(RESUME)"

docx:
	$(MAKE) clean
	$(MAKE) _docx

_docx: validate
	$(PYTHON_RUN) python scripts/render_docx.py --resume "$(RESUME)"

pdf:
	$(MAKE) clean
	$(MAKE) _pdf

_pdf: _docx
	$(PYTHON_RUN) python scripts/build_pdf.py --resume "$(RESUME)"

render-release:
	$(MAKE) clean
	$(MAKE) _render-markdown _render-structured _pdf

check:
	$(MAKE) clean
	$(MAKE) _render
	$(MAKE) check-unit check-markdown check-structured check-docx check-tika

check-unit:
	PYTHONPATH=scripts $(PYTHON_RUN) python -m unittest discover -s tests -p 'test_*.py'

check-markdown:
	$(PYTHON_RUN) python scripts/check_parse.py --resume "$(RESUME)"

check-structured:
	$(PYTHON_RUN) python scripts/check_structured_markdown.py --resume "$(RESUME)"

check-docx:
	$(PYTHON_RUN) python scripts/check_docx.py --resume "$(RESUME)"

check-tika:
	RESUME="$(RESUME)" scripts/check_tika_docker.sh

check-urls:
	$(PYTHON_RUN) python scripts/check_urls.py --resume "$(RESUME)"

check-office:
	$(MAKE) clean
	$(MAKE) _render-markdown _render-structured _pdf
	$(PYTHON_RUN) python scripts/check_office.py --resume "$(RESUME)"

clean:
	rm -rf output
