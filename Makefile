#!make

HIFY_VERSION := 3.2.0
TARGET := hisu87/hify

all: build latest

build:
	docker buildx create --use
	docker buildx build --platform=linux/amd64,linux/arm64 -t $(TARGET):$(HIFY_VERSION) --push .

latest:
	docker buildx create --use
	docker buildx build --platform=linux/amd64,linux/arm64 -t $(TARGET):latest --push .

clean:
	find downloads -type f -name "*.mp3" -exec rm -f {} \;

up:
	docker compose up --build -d

down:
	docker compose down
	docker rmi hify:latest

run:
	uv run python main.py web

format:
	uv run ruff format .; ruff check . --fix
	prettier --write frontend/src/.

lint:
	prettier --check frontend/src/.
	uv run ruff check .; ruff check . --diff

export:
	uv export --no-hashes --no-dev -o requirements.txt

changelog:
	github_changelog_generator -u hisu87 -p hify -o CHANGELOG --no-verbose
	@echo "Changelog generated at CHANGELOG"

test:
	npm run test --prefix frontend
	uv run pytest -x -s -v

version:
	@VERSION=$(word 2,$(MAKECMDGOALS)); \
	echo "Hify version: $$VERSION"; \
	./version.sh $$VERSION
	npm install --prefix frontend
	npm run build --prefix frontend
	uv run ruff format .; ruff check . --fix
	prettier --write frontend/src/.

doc:
	uv run zensical serve

%:
	@:

.PHONY: all build latest clean up down run format lint export changelog version doc