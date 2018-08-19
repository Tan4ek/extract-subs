FROM 'python:3.6'

WORKDIR /usr/src/app

COPY requirements.txt ./
COPY extract-subs.py ./

RUN pip install --no-cache-dir -r requirements.txt