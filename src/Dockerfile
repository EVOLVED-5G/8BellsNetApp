FROM python:3.8.10
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y jq && apt-get clean

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
ADD . /usr/src/app/
COPY requirements.txt /usr/src/app/
RUN pip3 install evolved5g==1.0.2
RUN pip install -r requirements.txt

CMD ["sh", "prepare.sh"]





