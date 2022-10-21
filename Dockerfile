FROM python:3.7.4-alpine3.10
RUN apk add --no-cache --virtual .build-deps g++ python3-dev libffi-dev openssl-dev && \
    apk add --no-cache --update python3 && \
    pip3 install --upgrade pip setuptools
RUN pip3 install pendulum service_identity
RUN mkdir /app
WORKDIR /app
COPY app/requirements.txt /app/requirements.txt
COPY app /app
RUN python -m pip install --upgrade pip
RUN pip install PyMySQL
RUN pip --no-cache-dir install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["app.py"]
#CMD ["python","./app.py"]






