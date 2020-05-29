import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')
django.setup()
from run_init import *
from django.db.models import Sum, Count

now = datetime.datetime.now()
# Member.objects.filter(order__created_at__gt=now).annotate(Sum('order'))[0].order__count
# Member.objects.filter(order__created_at__gt=now).annotate(total_price=Sum('order__total_price')).filter(
#     total_price__gt=151156)
q = Member.objects.all().first()
q = Member.objects.annotate(Count('id'))
q = RewardRecord.objects.order_by('member__id').values('member__id').distinct()
q = RewardRecord.objects.values('member__id').distinct()

# City.objects.values('name', 'country__name').annotate(Sum('population'))
q = Member.objects.filter(reward__total_point__gt=1).distinct()
for el in q.first().reward.all():
    print(el.point, el.total_point, el.created_at)
i = Member.objects.annotate(Sum('reward__point')).filter(reward__point__sum__gte=179)
q = Member.objects.annotate(Sum('reward__point')).filter(reward__point__sum__gte=179, reward__point__sum__lte=179)
q[1].reward__point__sum
i.reward__point__sum
i.reward.first().total_point
q = q.order_by('member__id').distinct('member__id')
print(q.query)
for el in q:
    print(el.point, el.total_point, el.created_at)
print(q.query)
