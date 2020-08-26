# from log import logger
import requests
from ..run_init import *


# logger.info('demo')
def demo():
    now = timezone.now().date()
    members = Member.objects.all()
    for member in members:
        record = RewardRecord.objects.filter(member=member).first()
        temps = RewardRecordTemp.objects.filter(member=member).all()
        if now == record.end_date and record.total_point != 0:
            RewardRecord.objects.create(
                member=member,
                order=None,
                desc=f'{record.end_date}回饋點數到期',
                manual=False,
                point=record.total_point * -1,
                total_point=0,
                end_date=record.end_date,
                use_point=record.use_point,
            )
        for temp in temps:
            record = RewardRecord.objects.filter(member=member).first()
            if now == temp.start_date:
                rrecord = RewardRecord.objects.filter(member=member).filter(desc__icontains='回饋點數到期').first()
                if temp.order.created_at.date() <= rrecord.end_date <= now and record.total_point == 0 and rrecord.point < 0:
                    RewardRecord.objects.create(
                        member=member,
                        order=None,
                        desc=f'{now}回饋點數延期',
                        manual=False,
                        point=rrecord.point * -1,
                        total_point=rrecord.point * -1,
                        end_date=temp.end_date,
                        use_point=rrecord.use_point,
                    )
                record = RewardRecord.objects.filter(member=member).first()
                RewardRecord.objects.create(
                    member=member,
                    order=temp.order,
                    desc=temp.desc,
                    manual=False,
                    point=temp.point,
                    total_point=record.total_point + temp.point,
                    end_date=temp.end_date,
                    use_point=record.use_point,
                )
                temp.delete()


