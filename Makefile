.PHONY: install synth deploy destroy diff test lint format update-deps pr

install:
	uv sync --dev
	npm install

synth:
	npx cdk synth

deploy:
	npx cdk deploy --require-approval broadening

destroy:
	npx cdk destroy --force

diff:
	npx cdk diff

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check .
	uv run ruff format --check .
	npx markdownlint '**/*.md' --ignore node_modules

format:
	uv run ruff check --fix .
	uv run ruff format .

update-deps:
	uv lock --upgrade
	uv sync --dev
	npm update

pr: lint test synth

