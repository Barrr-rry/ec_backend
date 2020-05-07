from django.db.models import Q
from rest_framework import filters
from rest_framework.compat import coreapi, coreschema
from django.utils import timezone

or_q = lambda q, other_fn: other_fn if q is None else q | other_fn
and_q = lambda q, other_fn: other_fn if q is None else q & other_fn


class MemberFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        q = None
        keywords = request.query_params.get('keywords')
        if keywords is not None:
            q = or_q(q, Q(member_number__contains=keywords))
            q = or_q(q, Q(phone__contains=keywords))
            q = or_q(q, Q(cellphone__contains=keywords))
            q = or_q(q, Q(account__contains=keywords))
            q = or_q(q, Q(name__contains=keywords))

        status = request.query_params.get('status')
        if status is not None:
            q = and_q(q, Q(status=status))

        order_by = request.query_params.get('order_by')
        if order_by:
            order_by = order_by.replace('join_at', 'created_at')
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
                name='status',
                required=False,
                location='query',
                schema=coreschema.String(
                    title='status',
                    description='bool: 帳號狀態',
                    format='bool',
                )
            ),
        )


class OrderFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        q = None
        keywords = request.query_params.get('keywords')
        if keywords is not None:
            q = or_q(q, Q(shipping_name__contains=keywords))
            q = or_q(q, Q(phone__contains=keywords))
            q = or_q(q, Q(order_number__contains=keywords))

        to_store = request.query_params.get('to_store')
        if to_store is not None:
            q = and_q(q, Q(to_store=to_store))

        simple_status = request.query_params.get('simple_status')
        if simple_status is not None:
            q = and_q(q, Q(simple_status=simple_status))

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

        )


class ProductFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, queryset, view):
        q = None
        keywords = request.query_params.get('keywords')
        if keywords is not None:
            for keyword in keywords.strip().split():
                q = or_q(q, Q(product_number__contains=keyword))
                q = or_q(q, Q(brand__en_name__contains=keyword))
                q = or_q(q, Q(brand__cn_name__contains=keyword))
                q = or_q(q, Q(name__contains=keyword))

        brand = request.query_params.get('brand')
        if brand is not None:
            q = and_q(q, Q(brand=brand))

        tag = request.query_params.get('tag')
        if tag is not None:
            q = and_q(q, Q(tag=tag))

        order_by = request.query_params.get('order_by')
        if order_by:
            queryset = queryset.order_by(order_by)

        category = request.query_params.get('category')
        if category is not None:
            q = and_q(q, Q(category=category))

        no_tag = request.query_params.get('no_tag')
        if no_tag is not None:
            q = and_q(q, Q(tag__isnull=True))

        order_by = request.query_params.get('order_by')
        if order_by:
            queryset = queryset.order_by(order_by)

        only_tag = request.query_params.get('only_tag')
        if only_tag is not None:
            q = and_q(q, Q(tag__isnull=False))

        inventory_status = request.query_params.get('inventory_status')
        if inventory_status is not None:
            q = and_q(q, Q(inventory_status=inventory_status))

        max_price = request.query_params.get('max_price')
        min_price = request.query_params.get('min_price')
        if max_price is not None:
            q = and_q(q, Q(price__lte=max_price))
        if min_price is not None:
            q = and_q(q, Q(price__gte=min_price))

        ids = request.query_params.get('ids')
        if ids:
            ids = ids.split(',')
            q = and_q(q, Q(id__in=ids))

        if q:
            return queryset.filter(q)
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
                    description='int: 庫存狀況 1：有庫存；2：無庫存；3：預品'
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
