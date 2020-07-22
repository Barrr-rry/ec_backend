from loguru import logger
import datetime

# https://cuiqingcai.com/7776.html
# https://blog.csdn.net/mouday/article/details/88560543
logger.add(
    f'./logs/{datetime.date.today():%Y%m%d}.log',
    rotation='1 day',
    retention='7 days',
    level='INFO',
)

logger.add(
    f'./logs/{datetime.date.today():%Y%m%d}_error.log',
    rotation='1 day',
    retention='7 days',
    level='ERROR',
)

logger.add(
    f'./logs/{datetime.date.today():%Y%m%d}_ecpay.log',
    rotation='1 day',
    retention='1 days',
    level='INFO',
    backtrace=True, diagnose=True,
    filter=lambda record: record["extra"].get("name") == "ecpay"
)
ecpay_loggger = logger.bind(name='ecpay')
