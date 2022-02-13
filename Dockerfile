FROM python:3.8-alpine3.15 AS dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir --user --no-warn-script-location -r requirements.txt

FROM python:3.8-alpine3.15 AS build-image
COPY --from=dependencies /root/.local /root/.local

WORKDIR /usr/src/app

# version of alpine https://github.com/docker-library/python/blob/master/3.8/alpine3.15/Dockerfile
# version of mkvtoolnix https://pkgs.alpinelinux.org/packages?name=mkvtoolnix&branch=v3.15
RUN apk add --no-cache 'mkvtoolnix=>63.0'

COPY src ./src
COPY extract_subs.py ./
# Make sure scripts in .local are usable:
ENV PATH=/root/.local/bin:$PATH

ENTRYPOINT ["python", "extract_subs.py"]