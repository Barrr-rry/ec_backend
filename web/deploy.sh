#!/bin/sh

docker exec -it public-ec-django-web python before_deploy.py
docker-compose -f docker-compose_pd.yml up --build -d
docker exec -it public-ec-django-web python after_deploy.py