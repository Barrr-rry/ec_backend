from django.db.models import Q, Sum, Count
from rest_framework import filters
from rest_framework.compat import coreapi, coreschema
from django.utils import timezone
from django.utils.timezone import make_aware
from dateutil.relativedelta import relativedelta
import datetime

# queryset 查詢的語法
or_q = lambda q, other_fn: other_fn if q is None else q | other_fn
and_q = lambda q, other_fn: other_fn if q is None else q & other_fn


class MemberFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        q = None
        # filter keywords
        keywords = request.query_params.get('keywords')
        if keywords is not None:
            q = or_q(q, Q(member_number__icontains=keywords))
            q = or_q(q, Q(phone__contains=keywords))
            q = or_q(q, Q(cellphone__contains=keywords))
            q = or_q(q, Q(account__icontains=keywords))
            q = or_q(q, Q(name__icontains=keywords))

        # filter status
        status = request.query_params.get('status')
        if status is not None:
            q = and_q(q, Q(status=status))

        # filter size
        sizes = request.query_params.get('size')
        if sizes is not None:
            for size in sizes.split(','):
                q = and_q(q, Q(memberspec__name__icontains=size))

        # filter gender
        gender = request.query_params.get('gender')
        if gender is not None and gender != '0':
            q = and_q(q, Q(gender=gender))

        # filter local
        local = request.query_params.get('local')
        if local is not None and local != '0':
            local_map = {'1': '台灣', '2': '海外'}
            local = local_map[local]
            q = and_q(q, Q(local=local))

        # filter reward point
        reward_upper = request.query_params.get('reward_upper')
        reward_lower = request.query_params.get('reward_lower')
        if reward_lower is not None or reward_upper is not None:
            queryset = queryset.annotate(Sum('reward__point'))
        if reward_upper is not None:
            q = and_q(q, Q(reward__point__sum__lte=reward_upper))
        if reward_lower is not None:
            q = and_q(q, Q(reward__point__sum__gte=reward_lower))

        # filter birthday
        age_upper = request.query_params.get('age_upper')
        age_lower = request.query_params.get('age_lower')
        now = datetime.datetime.now()
        if age_upper is not None:
            bir_upper = (now - relativedelta(years=int(age_upper))).strftime('%Y-%m-%d')
            q = and_q(q, Q(birthday__gte=bir_upper))
        if age_lower is not None:
            bir_lower = (now - relativedelta(years=int(age_lower))).strftime('%Y-%m-%d')
            q = and_q(q, Q(birthday__lte=bir_lower))

        # filter bmi
        bmi_upper = request.query_params.get('bmi_upper')
        bmi_lower = request.query_params.get('bmi_lower')
        if bmi_upper is not None:
            q = and_q(q, Q(bmi__lte=bmi_upper))
        if bmi_lower is not None:
            q = and_q(q, Q(bmi__gte=bmi_lower))

        # filter order time
        start_date = request.query_params.get('start_date')
        if start_date:
            start_date = make_aware(datetime.datetime.strptime(start_date, '%Y-%m-%d'))
            q = and_q(q, Q(order__created_at__gte=start_date))
        end_date = request.query_params.get('end_date')
        if end_date:
            end_date = make_aware(datetime.datetime.strptime(end_date, '%Y-%m-%d'))
            q = and_q(q, Q(order__created_at__lte=end_date))

        # filter paytotal
        money_upper = request.query_params.get('money_upper')
        money_lower = request.query_params.get('money_lower')
        order_count_upper = request.query_params.get('order_count_upper')
        order_count_lower = request.query_params.get('order_count_lower')
        if money_lower:
            q = and_q(q, Q(pay_total__gte=money_lower))
        if money_upper:
            q = and_q(q, Q(pay_total__lte=money_upper))

        # filter order count
        if order_count_upper:
            q = and_q(q, Q(order_count__lte=order_count_upper))
        if order_count_lower:
            q = and_q(q, Q(order_count__gte=order_count_lower))

        # order by
        order_by = request.query_params.get('order_by')
        if order_by:
            order_by = order_by.replace('join_at', 'created_at')
            if 'returns' in order_by:
                queryset = queryset.annotate(returns=Sum('reward__point'))
            if 'reward_end_date' in order_by:
                order_by = '-reward__end_date' if '-' in order_by else 'reward__end_date'
            queryset = queryset.order_by(order_by)
        if q:
            return queryset.filter(q)
        else:
            return queryset

    def get_schema_fields(self, view):
        if view.action != 'list':
            return []
        return (
            coreapi.Field(
                name='keywords',
                required=False,
                location='query',
                schema=coreschema.String(
                    # location='query',
                    title='keywords',
                    description='str: 請輸入Keywords'
                )
            ),
            coreapi.Field(
                name='order_by',
                required=False,
                # location='query',
                schema=coreschema.String(
                    title='order_by',
                    description='str: 排序'
                )
            ),
            coreapi.Field(
                name='status',
                required=False,
                schema=coreschema.String(
                    title='status',
                    description='bool: 帳號狀態',
                    format='bool',
                )
            ),
            coreapi.Field(
                name='reward_upper',
                required=False,
                # location='query',
                schema=coreschema.Number(
                    title='reward_upper',
                    description='int: 回饋金點數上限'
                )
            ),
            coreapi.Field(
                name='age_upper',
                required=False,
                # location='query',
                schema=coreschema.Number(
                    title='age_upper',
                    description='int: 年齡上限'
                )
            ),
            coreapi.Field(
                name='age_lower',
                required=False,
                # location='query',
                schema=coreschema.Number(
                    title='age_lower',
                    description='int: 年齡下限'
                )
            ),
            coreapi.Field(
                name='bmi_upper',
                required=False,
                # location='query',
                schema=coreschema.Number(
                    title='bmi_upper',
                    description='int: BMI上限'
                )
            ),
            coreapi.Field(
                name='bmi_lower',
                required=False,
                # location='query',
                schema=coreschema.Number(
                    title='bmi_lower',
                    description='int: BMI下限'
                )
            ),
            coreapi.Field(
                name='gender',
                required=False,
                # location='query',
                schema=coreschema.Number(
                    title='gender',
                    description='int: 性別'
                )
            ),
            coreapi.Field(
                name='local',
                required=False,
                # location='query',
                schema=coreschema.Number(
                    title='local',
                    description='int: 所在地'
                )
            ),
            coreapi.Field(
                name='size',
                required=False,
                # location='query',
                schema=coreschema.String(
                    title='size',
                    description='str: 尺寸'
                )
            ),
            coreapi.Field(
                name='reward_lower',
                required=False,
                # location='query',
                schema=coreschema.Number(
                    title='reward_lower',
                    description='int: 回饋金點數下限'
                )
            ),
        )


class OrderFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        q = None
        # filter keywords
        keywords = request.query_params.get('keywords')
        if keywords is not None:
            q = or_q(q, Q(shipping_name__icontains=keywords))
            q = or_q(q, Q(phone__contains=keywords))
            q = or_q(q, Q(order_number__contains=keywords))

        # filte to_store
        to_store = request.query_params.get('to_store')
        if to_store is not None:
            q = and_q(q, Q(to_store=to_store))

        # filter simple status
        simple_status = request.query_params.get('simple_status')
        if simple_status is not None:
            q = and_q(q, Q(simple_status=simple_status))

        # filter ids
        ids = request.query_params.get('ids')
        if ids:
            ids = ids.split(',')
            q = and_q(q, Q(id__in=ids))

        # order by
        order_by = request.query_params.get('order_by')
        if order_by:
            queryset = queryset.order_by(order_by)

        if q:
            return queryset.filter(q)
        else:
            return queryset

    def get_schema_fields(self, view):
        if view.action != 'list':
            return []
        return (
            coreapi.Field(
                name='keywords',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='keywords',
                    description='str: 請輸入Keywords'
                )
            ),
            coreapi.Field(
                name='order_by',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='order_by',
                    description='str: 排序'
                )
            ),
            coreapi.Field(
                name='to_store',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='to_store',
                    description='bool: 物流狀態',
                    format='bool',
                )
            ),
            coreapi.Field(
                name='simple_status',
                required=False,
                location='query',
                schema=coreschema.Number(
                    title='simple_status',
                    description='str: 訂單狀態',
                )
            ),
            coreapi.Field(
                name='ids',
                required=False,
                location='query',
                schema=coreschema.Array(
                    title='ids',
                    description='array: ids'
                )
            ),

        )


class ProductFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        q = None
        keywords = request.query_params.get('keywords')
        if keywords is not None:
            for keyword in keywords.strip().split():
                q = or_q(q, Q(product_number__icontains=keyword))
                q = or_q(q, Q(brand__en_name__icontains=keyword))
                q = or_q(q, Q(brand__cn_name__icontains=keyword))
                q = or_q(q, Q(specifications_detail__product_code__icontains=keyword))
                q = or_q(q, Q(name__icontains=keyword))
                q = or_q(q, Q(en_name__icontains=keyword))

        # filter brand
        brand = request.query_params.get('brand')
        if brand is not None:
            q = and_q(q, Q(brand=brand))

        # filter tag
        tag = request.query_params.get('tag')
        if tag is not None:
            q = and_q(q, Q(tag=tag))

        # order_by
        order_by = request.query_params.get('order_by')
        if order_by:
            queryset = queryset.order_by(order_by)

        # filter category
        category = request.query_params.get('category')
        if category is not None:
            q = and_q(q, Q(category=category))
        category_ids = request.query_params.get('category_ids')
        if category_ids is not None:
            category_ids = category_ids.split(',')
            q = and_q(q, Q(id__in=category_ids))
            q = and_q(q, Q(category=category))

        # filter tag
        no_tag = request.query_params.get('no_tag')
        if no_tag is not None:
            q = and_q(q, Q(tag__isnull=True))
        only_tag = request.query_params.get('only_tag')
        if only_tag is not None:
            q = and_q(q, Q(tag__isnull=False))

        # filter status
        status = request.query_params.get('status')
        if status is not None:
            status = bool(int(status))
            q = and_q(q, Q(status=status))

        # filter inventory_status & spec
        inventory_status = request.query_params.get('inventory_status')
        if inventory_status is not None:
            inventory_status = int(inventory_status)
            if inventory_status == 1:
                q = and_q(q, ~Q(specifications_detail__quantity__lte=10))
            if inventory_status == 2:
                q = and_q(q, Q(specifications_detail__quantity__lte=0))
            elif inventory_status == 3:
                q = and_q(q, ~Q(specifications_detail__quantity__lte=0))
                q = and_q(q, Q(specifications_detail__quantity__lte=10))

        inventory_status_2 = request.query_params.get('inventory_status_2')
        if inventory_status_2 is not None:
            inventory_status_2 = int(inventory_status_2)
            q = and_q(q, Q(specifications_detail__inventory_status=inventory_status_2))

        max_price = request.query_params.get('max_price')
        min_price = request.query_params.get('min_price')
        if max_price is not None:
            q = and_q(q, Q(specifications_detail__price__lte=max_price))
        if min_price is not None:
            q = and_q(q, Q(specifications_detail__price__gte=min_price))

        # filter ids
        ids = request.query_params.get('ids')
        if ids:
            ids = ids.split(',')
            q = and_q(q, Q(id__in=ids))

        if q:
            return queryset.filter(q).distinct()
        else:
            return queryset

    def get_schema_fields(self, view):
        if view.action != 'list':
            return []
        return (
            coreapi.Field(
                name='ids',
                required=False,
                location='query',
                schema=coreschema.Array(
                    title='ids',
                    description='array: ids'
                )
            ),
            coreapi.Field(
                name='order_by',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='order_by',
                    description='str: 排序'
                )
            ),
            coreapi.Field(
                name='keywords',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='keywords',
                    description='str: 請輸入Keywords'
                )
            ),
            coreapi.Field(
                name='brand',
                required=False,
                location='query',
                schema=coreschema.Number(
                    title='brand',
                    description='int: 品牌'
                )
            ),
            coreapi.Field(
                name='tag',
                required=False,
                location='query',
                schema=coreschema.Number(
                    title='tag',
                    description='int: 標籤'
                )
            ),
            coreapi.Field(
                name='category',
                required=False,
                location='query',
                schema=coreschema.Number(
                    title='category',
                    description='int: 分類'
                )
            ),
            coreapi.Field(
                name='category_ids',
                required=False,
                location='query',
                schema=coreschema.Array(
                    title='category ids',
                    description='array: 分類 ids'
                )
            ),
            coreapi.Field(
                name='no_tag',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='no_tag',
                    description='str: 沒有標籤'
                )
            ),
            coreapi.Field(
                name='inventory_status',
                required=False,
                location='query',
                schema=coreschema.Number(
                    title='inventory_status',
                    description='int: 庫存狀況 0：全部；1：庫存充足；2：庫存不足；3：無庫存'
                )
            ),
            coreapi.Field(
                name='inventory_status_2',
                required=False,
                location='query',
                schema=coreschema.Number(
                    title='inventory_status_2',
                    description='int: 庫存狀況 0：全部；1：庫存充足；2：庫存不足；3：無庫存'
                )
            ),
            coreapi.Field(
                name='max_price',
                required=False,
                location='query',
                schema=coreschema.Number(
                    title='max_price',
                    description='int: 金額上限'
                )
            ),
            coreapi.Field(
                name='min_price',
                required=False,
                location='query',
                schema=coreschema.Number(
                    title='min_price',
                    description='int: 金額下限'
                )
            ),
            coreapi.Field(
                name='order_by',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='order_by',
                    description='str: 排序'
                )
            ),
            coreapi.Field(
                name='status',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='status',
                    description='bool: 上架狀態',
                    format='bool',
                )
            ),
        )


class CouponFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        q = None
        discount_code = request.query_params.get('discount_code')
        if discount_code is not None:
            return queryset.filter(discount_code=discount_code)

        return queryset

    def get_schema_fields(self, view):
        if view.action != 'list':
            return []
        return (
            coreapi.Field(
                name='discount_code',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='discount_code',
                    description='str: 請輸入Filter'
                )
            ),
        )


class ActivityFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        q = None
        keywords = request.query_params.get('keywords')
        if keywords is not None:
            for keyword in keywords.strip().split():
                q = or_q(q, Q(ch_name__icontains=keyword))
                q = or_q(q, Q(en_name__icontains=keyword))

        if q:
            return queryset.filter(q)
        else:
            return queryset

    def get_schema_fields(self, view):
        if view.action != 'list':
            return []
        return (
            coreapi.Field(
                name='keywords',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='keywords',
                    description='str: 請輸入Keywords'
                )
            ),
        )
