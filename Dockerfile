FROM python:3.11.18-alpine AS dependencies
COPY requirements.txt .

RUN python -m pip install --no-cache-dir --upgrade 'pip>=26.2.2'
RUN pip install --no-cache-dir --user --no-warn-script-location -r requirements.txt

FROM python:3.11.18-alpine AS build-image
COPY --from=dependencies /root/.local /root/.local

WORKDIR /usr/src/app

RUN apk add --no-cache 'mkvtoolnix=>63.0'

COPY src ./src
COPY extract_subs.py ./
# Make sure scripts in .local are usable:
ENV PATH=/root/.local/bin:$PATH

ENTRYPOINT ["python", "extract_subs.py"]
