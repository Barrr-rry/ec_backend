#!/bin/sh
rm api/migrations/00*.py
rm test.db
python clear_mysql.py
python manage.py makemigrations
python manage.py migrate
python run_init.py