FROM python:3.14
LABEL "Maintained"=""
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["app.py"]