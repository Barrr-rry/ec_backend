import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')
django.setup()
from run_init import *
from django.db.models import Sum, Count
from django.utils.timezone import make_aware
import datetime

now = datetime.datetime.now()
# Member.objects.filter(order__created_at__gt=now).annotate(Sum('order'))[0].order__count
# Member.objects.filter(order__created_at__gt=now).annotate(total_price=Sum('order__total_price')).filter(
#     total_price__gt=151156)
date1 = '2020-05-29'
date2 = '2020-06-06'
date1 = make_aware(datetime.datetime.strptime(date1, '%Y-%m-%d'))
date2 = make_aware(datetime.datetime.strptime(date2, '%Y-%m-%d'))
mony_lower = 30
q = Member.objects.filter(order__created_at__gte=date1, order__created_at__lte=date2)
q = q.annotate(Sum('order__total_price'))
q[0].order__total_price__sum
print()
