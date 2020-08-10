import uuid
import pickle
from django.core.cache import cache
from .models import ConfigSetting
from . import serializers


class PickleRedis:
    """
    將資料轉成pickle 做進出 而且存成pickle 好處多多
    也可以將class 也寫成pickle
    """
    def __init__(self, r=None):
        self.r = r

    def set_data(self, key, data):
        fkey = f'nuxt:{key}'
        self.r.set(fkey, pickle.dumps(data))

    def remove_data(self, key):
        fkey = f'nuxt:{key}'
        self.r.delete(fkey)

    def get_data(self, key):
        fkey = f'nuxt:{key}'
        data = self.r.get(fkey)
        if data is not None:
            return pickle.loads(data)


# init cache
default_cache = dict()
cache_list = ['coupon', 'product', 'banner', 'caetegory', 'tag', 'price', 'brand']
for key in cache_list:
    default_cache[key] = str(uuid.uuid4())

pickle_redis = PickleRedis(cache)
pickle_redis.set_data('cache', default_cache)


def get_config():
    """
    將config 資料作成cache
    :return: config
    """
    key = 'configsetting'
    data = pickle_redis.get_data(key)
    if not data:
        instance = ConfigSetting.objects.first()
        data = serializers.ConfigSettingSerializer(instance=instance).data
        pickle_redis.set_data('configsetting', data)
    return data
