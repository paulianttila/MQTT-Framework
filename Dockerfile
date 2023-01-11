FROM python:3.11-alpine

RUN apk update && apk add --no-cache git

WORKDIR /tmp/install
ADD . .
RUN pip install --no-cache-dir -r requirements.txt && python setup.py install && rm -rf /tmp/install
WORKDIR /

CMD python