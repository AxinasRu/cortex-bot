FROM python
RUN apt-get update && \
    apt-get install -y locales && \
    sed -i -e 's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales
ENV LANG ru_RU.UTF-8
ENV LC_ALL ru_RU.UTF-8
COPY . /app
WORKDIR /app
RUN curl -sSL https://install.python-poetry.org | python3 -
RUN ~/.local/bin/poetry config virtualenvs.create false
RUN ~/.local/bin/poetry install
CMD ~/.local/bin/poetry run cortex