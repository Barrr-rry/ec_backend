from run_init import *

from log import logger
import traceback
from django.http import HttpResponse
import requests
import os
from api.util import pickle_redis, get_config

token = 'PAy6SmSfpfEI6nNN8K4cQKsUcjve4kxCWg03B49Tqt4'
DEBUG = os.environ.get('ENV') != 'prod'


def line_notify(msg):
    """
    line 通知功能
    """
    # 開發機 不需要通知 不然會收不完
    if DEBUG:
        return
    url = "https://notify-api.line.me/api/notify"

    headers = {
        "Authorization": "Bearer " + token
    }

    payload = {'message': msg}
    r = requests.post(url, headers=headers, params=payload)
    return r.status_code


# 更新狀態成 維護
instance = ConfigSetting.objects.first()
if not instance:
    ConfigSetting.objects.create(
        in_maintenance=True
    )
else:
    instance.in_maintenance = True
    instance.save()

for key in pickle_redis.r.keys('*'):
    pickle_redis.r.delete(key)

line_notify('準備部署')
logger.info('準備部署')
