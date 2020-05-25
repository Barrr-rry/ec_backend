# from log import logger


def demo():
    # logger.info('demo')
    msg = 'test'
    token = 'FtiyBzeoeH6OQ02pkgnh1A89LWW6SiCH04kqR0kV3nc'
    import requests
    url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": "Bearer " + token
    }

    payload = {'message': msg}
    r = requests.post(url, headers=headers, params=payload)
