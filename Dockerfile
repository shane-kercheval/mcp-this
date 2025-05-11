FROM python:3.13

WORKDIR /code
ENV PYTHONPATH "${PYTHONPATH}:/code"

ENV PYDEVD_WARN_EVALUATION_TIMEOUT 1000

RUN apt-get update -y && apt-get install zsh -y
RUN PATH="$PATH:/usr/bin/zsh"

RUN apt-get install lsof

RUN python -m pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN rm requirements.txt
