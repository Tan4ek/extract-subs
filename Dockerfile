FROM python:3.8-alpine AS dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir --user --no-warn-script-location -r requirements.txt

FROM python:3.8-alpine AS build-image
COPY --from=dependencies /root/.local /root/.local

WORKDIR /usr/src/app

COPY extract-subs.py extract_mkv_info.py iso639_json_parser.py mergesubs.py util.py ./
# version of alpine https://github.com/docker-library/python/blob/master/3.8/alpine3.12/Dockerfile
# version of mkvtoolnix https://pkgs.alpinelinux.org/packages?name=mkvtoolnix&branch=v3.12
RUN apk add --no-cache 'mkvtoolnix=>46.0'
# Make sure scripts in .local are usable:
ENV PATH=/root/.local/bin:$PATH

ENTRYPOINT ["python", "extract-subs.py"]