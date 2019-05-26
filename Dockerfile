FROM 'python:3.6'

WORKDIR /usr/src/app

COPY requirements.txt ./
COPY extract-subs.py ./
COPY mergesubs.py ./
COPY iso639_json_parser.py ./

RUN pip install --no-cache-dir -r requirements.txt
RUN wget -q -O - https://mkvtoolnix.download/gpg-pub-moritzbunkus.txt | apt-key add -
RUN apt-get update
RUN apt-get install -y mkvtoolnix

ENTRYPOINT ["python", "extract-subs.py"]