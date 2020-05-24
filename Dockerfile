FROM python:3.7
ENV ENV dev
COPY ./web /app
WORKDIR /app
RUN pip install -r requirements.txt
#RUN apt-get update && apt-get install -y cron
#RUN service cron start
#RUN python manage.py crontab add