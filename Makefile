.PHONY: clean-pyc clean-build docs

TAG := $(shell git describe master --abbrev=0)
TAGSTEEM := $(shell git describe master --abbrev=0 | tr "." "-")

# 
clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -fr __pycache__/

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

lint:
	flake8 steemapi/

build:
	python3 setup.py build

install: build
	python3 setup.py install

install-user: build
	python3 setup.py install --user

release: clean
	python3 setup.py check
	python3 setup.py sdist upload -r pypi
	python3 setup.py bdist --format=zip upload
	git tag -l -n100 $(TAG) | piston post --author xeroc --permlink "piston-changelog-$(TAGSTEEM)" --category steem --title "[Changelog] Piston $(TAG)" \
	piston edit "@xeroc/piston-readme" --file README.md
