import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')
django.setup()
from run_init import *
from django.db.models import Sum, Count

now = datetime.datetime.now()
# Member.objects.filter(order__created_at__gt=now).annotate(Sum('order'))[0].order__count
Member.objects.filter(order__created_at__gt=now).annotate(total_price=Sum('order__total_price')).filter(
    total_price__gt=151156)
print()
