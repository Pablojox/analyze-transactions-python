# Makefile

.PHONY: help install run

help:
	@echo "Available commands:"
	@echo "  make install - Install all dependencies"
	@echo "  make run - Run the application"

install:
	pip install -r requirements.txt

run:
	python -m src
