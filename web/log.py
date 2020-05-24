from loguru import logger
import datetime

# https://cuiqingcai.com/7776.html
# https://blog.csdn.net/mouday/article/details/88560543
logger.add(
    f'./logs/{datetime.date.today():%Y%m%d}.log',
    rotation='1 day',
    retention='7 days',
    level='INFO',
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}"
)

logger.add(
    f'./logs/{datetime.date.today():%Y%m%d}_error.log',
    rotation='1 day',
    retention='7 days',
    level='ERROR',
    format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}"
)
