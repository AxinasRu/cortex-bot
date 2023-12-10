FROM python:3.10-alpine
COPY . /app
WORKDIR /app
RUN curl -sSL https://install.python-poetry.org | python3 -
RUN ~/.local/bin/poetry config virtualenvs.create false
RUN ~/.local/bin/poetry install
CMD ~/.local/bin/poetry run cortex