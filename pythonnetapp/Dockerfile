FROM python:3.8.10
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y jq && apt-get clean

RUN mkdir -p /usr/src/app
# RUN cp -r . /usr/src/app/
WORKDIR /usr/src/app
# ADD ./ /usr/src/app/
ADD . /usr/src/app/
COPY requirements.txt /usr/src/app/
RUN pip3 install evolved5g
RUN pip install -r requirements.txt
# ADD . .

# ENTRYPOINT ["python"]
# CMD ["app.py"]

CMD ["sh", "prepare.sh"]

# CMD [ "python", "app.py", "--config", "container", "--host=0.0.0.0"] 
# ENTRYPOINT ["python3", "-u", "app.py"]




