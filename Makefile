PYTHON = python
NAME = metadns

lint:
	$(PYTHON) -mpyflakes $(NAME)
	$(PYTHON) -mpylint -d missing-docstring -r n $(NAME)

clean:
	find . -name '__pycache__' -exec rm -rf '{}' ';'
	find . -name '*.pyc' -exec rm -f '{}' ';'