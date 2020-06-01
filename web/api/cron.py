# from log import logger
import requests
from api.models import Member


# logger.info('demo')
instance = Member.objects.first()
msg = f'test: {instance.name}'
token = 'FtiyBzeoeH6OQ02pkgnh1A89LWW6SiCH04kqR0kV3nc'

url = "https://notify-api.line.me/api/notify"
headers = {
    "Authorization": "Bearer " + token
}

payload = {'message': msg}
r = requests.post(url, headers=headers, params=payload)
