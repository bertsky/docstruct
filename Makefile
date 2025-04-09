PYTHON = python3
PIP = pip3
PYTHONIOENCODING=utf8
PYTEST_ARGS ?= "-vv --workspace=all"

DOCKER_BASE_IMAGE = docker.io/ocrd/core:v3.3.0
DOCKER_TAG = ocrd/docstruct

help:
	@echo
	@echo "  Targets"
	@echo
	@echo "    deps         Install only Python deps via pip"
	@echo "    install      Install full Python package via pip"
	@echo "    install-dev  Install in editable mode"
	@echo "    build        Build binary and source Python package"
	@echo "    docker       Build a Docker image $(DOCKER_TAG) from $(DOCKER_BASE_IMAGE)"
	@echo "    test         Run tests via Pytest"
	@echo "    repo/assets  Clone OCR-D/assets to ./repo/assets"
	@echo "    tests/assets Copy to ./tests/assets"
	@echo ""
	@echo "  Variables"
	@echo ""
	@echo "    DOCKER_TAG  Docker container tag ($(DOCKER_TAG))"
	@echo "    PYTEST_ARGS Additional runtime options for pytest ($(PYTEST_ARGS))"
	@echo "                (See --help, esp. custom option --workspace)"

# Install Python deps via pip
deps:
	$(PIP) install -r requirements.txt

# Install Python package via pip
install:
	$(PIP) install .

install-dev:
	$(PIP) install -e .

build:
	$(PIP) install build wheel
	$(PYTHON) -m build .

# Run test
test: tests/assets
	$(PYTHON) -m pytest  tests --durations=0 $(PYTEST_ARGS)

#
# Assets
#

# Update OCR-D/assets submodule
.PHONY: repos always-update tests/assets
repo/assets: always-update
	git submodule sync --recursive $@
	if git submodule status --recursive $@ | grep -qv '^ '; then \
		git submodule update --init --recursive $@ && \
		touch $@; \
	fi

benner_herrnhuterey04_1748.ocrd.zip:
	wget https://github.com/OCR-D/gt_structure_text/releases/download/v1.5.0/$@

# Setup test assets
tests/assets: benner_herrnhuterey04_1748.ocrd.zip
tests/assets: repo/assets
	mkdir -p $@
	cp -a $</data/* $@
	$(foreach BAG,$(filter %.zip,$^),ocrd zip spill -d $@/$(basename $(BAG)) $(BAG))

docker:
	docker build \
	--build-arg DOCKER_BASE_IMAGE=$(DOCKER_BASE_IMAGE) \
	--build-arg VCS_REF=$$(git rev-parse --short HEAD) \
	--build-arg BUILD_DATE=$$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
	-t $(DOCKER_TAG) .

.PHONY: help deps install install-dev build docker
