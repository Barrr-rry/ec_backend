import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')
django.setup()

from django.db import connection
from django.core.management import call_command
from django.conf import settings


def drop_db(prefix=None):
    dbinfo = settings.DATABASES['default']
    cursor = connection.cursor()
    db_name = dbinfo["NAME"] if prefix is None else f'{prefix}_{dbinfo["NAME"]}'
    print("Dropping and creating database " + db_name)
    cursor.execute(
        "DROP DATABASE " + db_name + ";")
    print("Done")


def recreate_db(prefix=None):
    dbinfo = settings.DATABASES['default']
    cursor = connection.cursor()
    db_name = dbinfo["NAME"] if prefix is None else f'{prefix}_{dbinfo["NAME"]}'
    print("Dropping and creating database " + db_name)
    cursor.execute(
        "DROP DATABASE " + db_name + "; CREATE DATABASE " + db_name + "; USE " + db_name + ";")
    print("Done")


if __name__ == "__main__":
    recreate_db()
    # drop_db(prefix='test')
