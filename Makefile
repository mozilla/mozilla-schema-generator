.PHONY: help clean clean-pyc clean-build list test coverage release

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "release - package and upload a release"
	@echo "install-requirements - install the requirements for development"

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

lint:
	flake8 mozilla_schema_creator tests --max-line-length 100

test:
	py.test

coverage:
	pytest tests/ --cov=mozilla_schema_creator
	coverage report -m
	coverage html
	open htmlcov/index.html

release: clean
	python setup.py sdist upload
	python setup.py bdist_wheel upload

install-requirements:
	pip install -r requirements/requirements.txt
	pip install -r requirements/test_requirements.txt
