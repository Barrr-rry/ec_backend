# from log import logger
import requests


# logger.info('demo')
def demo():
    msg = f'test: testsssss'
    token = 'FtiyBzeoeH6OQ02pkgnh1A89LWW6SiCH04kqR0kV3nc'

    url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": "Bearer " + token
    }

    payload = {'message': msg}
    r = requests.post(url, headers=headers, params=payload)


demo()