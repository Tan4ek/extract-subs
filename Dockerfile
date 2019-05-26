FROM "python:3.6.8-alpine3.9"

WORKDIR /usr/src/app

COPY requirements.txt extract-subs.py mergesubs.py iso639_json_parser.py ./

RUN pip install --no-cache-dir -r requirements.txt && \
    apk add --no-cache 'mkvtoolnix=~29.0'

ENTRYPOINT ["python", "extract-subs.py"]