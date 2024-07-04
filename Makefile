# Makefile

.PHONY: help install run

help:
	@echo "Available commands:"
	@echo "  make install - Install all dependencies and create .env file"
	@echo "  make run - Run the application"

install: requirements .env

requirements:
	pip install -r requirements.txt

.env:
	@if [ ! -f .env ]; then \
		echo "Creating .env file with default values"; \
		echo "REGION=" > .env; \
		echo "AWS_ACCESS_KEY_ID=" >> .env; \
		echo "AWS_SECRET_ACCESS_KEY=" >> .env; \
		echo "USER_POOL_ID=" >> .env; \
		echo "SALT_EDGE_APP_ID=" >> .env; \
		echo "SALT_EDGE_SECRET=" >> .env; \
	else \
		echo ".env file already exists"; \
	fi

run:
	python -m src
