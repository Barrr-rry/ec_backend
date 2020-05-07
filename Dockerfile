FROM python:3.7
ENV ENV dev
COPY ./web /app
WORKDIR /app
RUN pip install -r requirements.txt