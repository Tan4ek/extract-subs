FROM "python:3.8-alpine"

WORKDIR /usr/src/app

COPY . ./

# version of alpine https://github.com/docker-library/python/blob/master/3.8/alpine3.12/Dockerfile
# version of mkvtoolnix https://pkgs.alpinelinux.org/packages?name=mkvtoolnix&branch=v3.12
RUN pip install --no-cache-dir -r requirements.txt && \
    apk add --no-cache 'mkvtoolnix=>46.0'

ENTRYPOINT ["python", "extract-subs.py"]