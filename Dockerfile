FROM python:3.12-slim
LABEL "Maintained"=""
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["app.py"]