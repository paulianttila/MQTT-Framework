FROM python:3.11-alpine

RUN apk update && apk add git

WORKDIR /tmp/install
ADD . .
RUN pip install -r requirements.txt && python setup.py install && rm -rf /tmp/install
WORKDIR /

CMD python