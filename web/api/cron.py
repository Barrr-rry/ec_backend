# from log import logger


def demo():
    # logger.info('demo')
    msg = 'test'
    token = 'TOKEN'
    import requests
    url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": "Bearer " + token
    }

    payload = {'message': msg}
    r = requests.post(url, headers=headers, params=payload)
    print('123123123213')
