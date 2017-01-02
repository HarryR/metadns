PYTHON = python
NAME = metadns

lint:
	$(PYTHON) -mpyflakes $(NAME)
	$(PYTHON) -mpylint -d missing-docstring -r n $(NAME)

clean:
	find . -name '__pycache__' -exec rm -rf '{}' ';'
	find . -name '*.pyc' -exec rm -f '{}' ';'

docker-build:
	docker build -t $(NAME) .

docker-run: docker-build
	docker run -ti $(NAME)

docker-dev: docker-build
	docker run -ti -v `pwd`:/app/dev --entrypoint /bin/bash $(NAME)