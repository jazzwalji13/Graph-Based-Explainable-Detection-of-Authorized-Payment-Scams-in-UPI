.PHONY: setup seed dev test build

setup:
	python make.py setup

seed:
	python make.py seed

dev:
	python make.py dev

test:
	python make.py test

build:
	python make.py build
