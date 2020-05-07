#!/bin/sh
rm api/migrations/00*.py
rm db.sqlite3
python clear_mysql.py
python manage.py makemigrations
python manage.py migrate
python run_init.py