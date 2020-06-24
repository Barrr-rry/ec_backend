from rest_framework import viewsets
from functools import partial
from functools import wraps
from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.mixins import \
    (CreateModelMixin, ListModelMixin, DestroyModelMixin, RetrieveModelMixin)
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_nested import routers
from rest_framework.parsers import MultiPartParser, FormParser
from .models import (BannerContent, Banner, File, Permission, Manager, AdminTokens, Member, Category, Tag, Brand,
                     Product, ConfigSetting, SpecificationDetail, Country, RewardRecordTemp, Reward, RewardRecord,
                     RewardRecordTemp, Activity, BlacklistRecord,
                     ProductImage, Cart, ProductQuitShot, TagImage, FreeShipping, Coupon, MemberStore)
from .serializers import (BannerSerializer, FileSerializer, PermissionSerializer, ManagerSerializer,
                          ManagerLoginSerializer,
                          MemberSerializer, CategorySerializer, TagSerializer, BrandSerializer, ProductSerializer,
                          CartSerializer, ProductQuitShotSerializer, TagImageSerializer, TagListSerializer,
                          ProductListSerializer, FreeShippingSerializer, CouponSerializer, MemberLoginSerializer,
                          MemberPasswordSerializer, BlackListRecordSerializer)
from . import permissions
from . import serializers
# todo 之後要加入回來
from .authentication import TokenAuthentication, MemberAuthentication, MemberCheckAuthentication, \
    TokenCheckAuthentication, MangerOrMemberAuthentication
from rest_framework.permissions import IsAuthenticated
from .viewlib import (List2RetrieveMixin, NestedViewSetBase)
from collections import OrderedDict
import datetime
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend
from django.http import QueryDict
from django.db.models import Q
from rest_framework.compat import coreapi, coreschema, distinct
from rest_framework import exceptions
from rest_framework.pagination import LimitOffsetPagination
import datetime
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from .sdk import ecpay
from django.http import HttpResponseRedirect
from . import docs
from . import filters
from django.db.models import Prefetch
from . import permissions
import json
from django.utils import timezone
from api.sdk import shipping_map
from api.mail.html_mail import send_mail
from django.contrib.auth.models import AnonymousUser
import os
from pyquery import PyQuery as pq
import requests
from log import logger

from django.utils.decorators import method_decorator
from django.db.models import Q, F
from .util import pickle_redis, get_config
import uuid
from django.db.models import Max, Min
from collections import defaultdict
import pandas as pd
import uuid

router = routers.DefaultRouter()
nested_routers = []
orderdct = OrderedDict()


class UpdateCache:
    prefix_key = None

    def update(self, *args, **kwargs):
        self.cache_process()
        return super().update(*args, **kwargs)

    def create(self, *args, **kwargs):
        self.cache_process()
        return super().create(*args, **kwargs)

    def destroy(self, *args, **kwargs):
        self.cache_process()
        return super().destroy(*args, **kwargs)

    def cache_process(self):
        if not self.prefix_key:
            return
        data = pickle_redis.get_data('cache')
        if not data:
            data = dict()
            cache_list = ['coupon', 'product', 'banner', 'caetegory', 'tag', 'price', 'configsetting']
            for key in cache_list:
                data[key] = str(uuid.uuid4())
        else:
            data[self.prefix_key] = str(uuid.uuid4())
        pickle_redis.set_data('cache', data)


class UpdateModelMixin:
    """
    客製化Update 不要有partial_update
    """

    def update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()


class MyMixin(CreateModelMixin, UpdateModelMixin, ListModelMixin, RetrieveModelMixin, DestroyModelMixin,
              viewsets.GenericViewSet):
    pass


def router_url(url, prefix=None, *args, **kwargs):
    def decorator(cls):
        if not prefix:
            router.register(url, cls, *args, **kwargs)
        else:
            prefix_router = orderdct.get(prefix, router)
            nested_router = routers.NestedDefaultRouter(prefix_router, prefix, lookup=prefix)
            nested_router.register(url, cls, *args, **kwargs)
            orderdct[url] = nested_router
            nested_routers.append(nested_router)

        @wraps(cls)
        def warp(*args, **kwargs):
            return cls(*args, **kwargs)

        return warp

    return decorator


@router_url('order')
class OrderViewSet(MyMixin):
    queryset = serializers.Order.objects.all()
    serializer_class = serializers.OrderSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = (filters.OrderFilter,)
    authentication_classes = [MangerOrMemberAuthentication]
    permission_classes = [(
            (permissions.OrderAuthenticated | permissions.OrderManagerEditPermission) & (
            permissions.OrderManagerReadPermission | permissions.OrderOwnaerPermission))]

    def get_queryset(self):
        queryset = super().get_queryset()
        if isinstance(self.request.user, Member):
            queryset.filter(member=self.request.user)
        return queryset

    def update(self, request, *args, **kwargs):
        if 'remark' in request.data:
            request.data['remark_date'] = timezone.now()
        return super().update(request, *args, **kwargs)


@router_url('ecpay')
class EcpayViewSet(GenericViewSet):
    # todo fake 看能不能有更好的寫法 沒有加會err
    queryset = serializers.Order.objects.all()
    serializer_class = serializers.OrderSerializer
    authentication_classes = [MemberCheckAuthentication]
    permission_classes = [permissions.DefaultIsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deerializing input, and for serializing output.
        """
        serializer_class = serializers.OrderSerializer
        kwargs['context'] = {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }
        return serializer_class(*args, **kwargs)

    def update_request(self, request):
        carts = request.user.cart.all()
        product_price = 0
        coupon_discount = 0
        # todo reward_discount check!!!
        reward_discount = request.data.get('reward_discount', 0)
        if 'reward_discount' in request.data:
            del request.data['reward_discount']
        freeshipping_price = 0
        total_weight = 0
        now = datetime.datetime.now()
        if not carts:
            raise serializers.serializers.ValidationError('no carts')
        product_shot = []
        # todo 沒有檢查庫存
        for cart in carts:
            # 更新商品 order count
            cart.product.order_count += cart.quantity
            cart.product.save()

            obj = serializers.ProductSerializer(cart.product).data
            product_price += cart.quantity * cart.specification_detail.price
            obj['specification_detail'] = serializers.SpecificationDetailSerializer(cart.specification_detail).data
            obj['quantity'] = cart.quantity
            total_weight += cart.specification_detail.weight * cart.quantity
            product_shot.append(obj)
        request.user.cart.all().delete()

        # coupon price discount
        coupon_id = request.data.get('coupon_id')
        coupon = Coupon.objects.get(pk=coupon_id) if coupon_id else None
        check_time = coupon and (coupon.start_time <= now.date() <= coupon.end_time or coupon.start_time is None and (
                coupon.end_time is None))
        if coupon and coupon.get_status(self.request.user) != 1:
            raise serializers.serializers.ValidationError('Coupon不正常')
        if coupon and check_time and coupon.role <= product_price:
            if coupon.method == 1:
                coupon_discount = coupon.discount
            else:
                coupon_discount = coupon.discount * product_price / 100
            coupon_discount = int(coupon_discount)
        # reward price discount
        if reward_discount > request.user.get_rewards():
            raise serializers.serializers.ValidationError('忠誠獎勵不符')

        """
        取得這個會員的點數
        取得最新一筆
        order_by end_date point小到大
        point 
        """
        queryset = RewardRecord.objects.filter(member=request.user)
        rewardrecord = queryset.first()
        queryset = queryset.filter(~Q(point=F('use_point')) & Q(point__gte=0)).order_by('end_date').order_by('point')
        if rewardrecord and rewardrecord.total_point < reward_discount:
            raise serializers.serializers.ValidationError('超出忠誠獎勵')

        if rewardrecord and reward_discount and rewardrecord.total_point >= reward_discount:
            temp_reward_discount = reward_discount
            for reward in queryset:
                point = reward.point
                if temp_reward_discount - point > 0:
                    point = 0
                else:
                    point = point - temp_reward_discount
                temp_reward_discount -= point

                reward.use_point = point
                reward.save()
                if not temp_reward_discount:
                    break

        # freeshipping price add
        freeshipping_id = request.data.get('freeshipping_id')
        freeshipping = serializers.FreeShipping.objects.get(pk=freeshipping_id)
        if freeshipping.weight >= total_weight:
            if freeshipping_price == 0 or freeshipping_price > freeshipping.price:
                freeshipping_price = freeshipping.price
            if freeshipping.role <= product_price:
                freeshipping_price = 0
        else:
            raise Exception('超出重量')
        activity_price = self.get_activity_price(carts)
        total_price = product_price + freeshipping_price - activity_price - coupon_discount - reward_discount
        request.data['product_shot'] = json.dumps(product_shot)
        request.data['total_price'] = total_price
        request.data['activity_price'] = activity_price
        request.data['freeshipping_price'] = freeshipping_price
        request.data['product_price'] = product_price
        request.data['coupon_price'] = coupon_discount
        request.data['reward_price'] = reward_discount
        return product_shot, total_price

    def get_activity_price(self, carts):
        ret = 0
        in_activity_obj = dict()
        for cart in carts:
            if not cart.product.activity:
                continue
            activity_id = cart.product.activity.id
            activity = cart.product.activity
            if activity_id not in in_activity_obj:
                in_activity_obj[activity_id] = dict(
                    activity=activity,
                    save_count=0,
                    product_count=0,
                    limit_count=activity.buy_count + activity.give_count,
                    price_list=[]
                )
            obj = in_activity_obj[activity_id]
            for i in range(cart.quantity):
                obj['price_list'].append(cart.specification_detail.price)
                obj['product_count'] += 1
            obj['save_count'] = (int(obj['product_count'] / obj['limit_count'])) * activity.give_count
            obj['price_list'] = sorted(obj['price_list'])
        a = [2, 3]
        for key, el in in_activity_obj.items():
            save_count = el['save_count']
            while save_count:
                save_count -= 1
                ret += el['price_list'].pop(0)

        return ret

    @action(methods=['POST'], detail=False)
    def repayment(self, request, *args, **kwargs):
        # todo no api no test
        order_id = request.data.get('order_id')
        url = request.data['callback_url']
        lang = request.data.get('lang', '')
        instance = serializers.Order.objects.get(pk=order_id)
        ret = {'html': ecpay.create_html(url, instance, lang=lang)}
        return Response(ret)

    @action(methods=['POST'], detail=False)
    def payment(self, request, *args, **kwargs):
        data = request.data
        if data.get('check_address'):
            user = request.user
            member_address_parmas = dict(
                member=user,
                shipping_name=data.get('shipping_name'),
                phone=data.get('phone'),
                shipping_address=data.get('shipping_address'),
                shipping_area=data.get('shipping_area'),
                location=data.get('location'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                country=data.get('country'),
                building=data.get('building'),
                company_name=data.get('company_name'),
                city=data.get('city'),
                postal_code=data.get('postal_code'),
            )
            instance = serializers.MemberAddress.objects.filter(
                **member_address_parmas,
            )
            if instance.count() == 0:
                instance = serializers.MemberAddress.objects.create(
                    **member_address_parmas,
                )
        url = data['callback_url']
        del data['callback_url']

        memberstore_id = data.get('memberstore_id')
        if memberstore_id:
            memberstore = serializers.MemberStore.objects.get(pk=memberstore_id)
            store_id = memberstore.store_id
            data['store_id'] = store_id
            data['address'] = memberstore.address
        with transaction.atomic():
            self.update_request(request)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            ret = serializer.data
            # 有金額才要處理金流
            if request.data['total_price']:
                lang = request.data.get('lang', '')
                ret['html'] = ecpay.create_html(url, serializer.instance, lang=lang)
            else:
                serializer.instance.pay_status = 1
                serializer.instance.simple_status_display = '已付款'
                serializer.instance.save()

            self.reward_process(serializer.instance)
        return Response(ret, status=status.HTTP_201_CREATED)

    def total_price_to_reward_point(self, total_price):
        # todo
        reward = serializers.Reward.objects.first()
        if reward.status == 1:
            point = (total_price // 100) * reward.discount

        elif reward.status == 2:
            point = int(total_price * (reward.discount / 100))
        else:
            raise

        return point

    @action(methods=['GET'], detail=False, permission_classes=[])
    def calc_reward(self, request, *args, **kwargs):
        # todo
        total_price = request.query_params.get('total_price')
        if total_price and isinstance(total_price, str):
            total_price = int(total_price)
            ret = dict(reward=self.total_price_to_reward_point(total_price))
        else:
            ret = dict(reward=0)
        return Response(ret)

    def reward_process(self, order):
        # 減少
        instance = RewardRecord.objects.filter(member=order.member).first()
        rewardrecord = RewardRecord.objects.create(
            member=order.member,
            order=order,
            point=-order.reward_price,
            total_point=instance.total_point - order.reward_price,
            desc=f'購物獎勵金折抵\n（ 訂單編號 : {order.order_number} ）'
        )
        # 新增
        self.to_reward(order)

    def to_reward(self, order):
        reward = serializers.Reward.objects.first()
        point = self.total_price_to_reward_point(order.total_price)
        start_date = datetime.datetime.now() + datetime.timedelta(days=reward.start_day)
        rewardrecord = RewardRecordTemp.objects.create(
            member=order.member,
            order=order,
            start_date=start_date,
            end_date=start_date + datetime.timedelta(days=reward.still_day),
            point=point,
            desc=f'購物獎勵金'
        )

    @action(methods=['POST', 'GET', 'DELETE', 'PUT'], detail=False, authentication_classes=[], permission_classes=[])
    def return_url(self, request, *args, **kwargs):
        logger.info('return url method: %s', request.stream.method)
        """payment return url"""
        logger.info('return url: %s', request.data['MerchantTradeNo'])
        instance = serializers.Order.objects.filter(order_number=request.data['MerchantTradeNo'][:-2]).first()
        if not instance:
            print('no return instance:', request.data['MerchantTradeNo'])
        if int(request.data['RtnCode']) == 1:
            instance.pay_status = 1
            instance.simple_status_display = '待出貨'
            instance.simple_status = 1
            # 如果是超商付款成功後建立物流
            if instance.to_store:
                ecpay.shipping(instance.store_type, instance.store_id, instance)
        if int(request.data['RtnCode']) == 10100141:
            instance.simple_status_display = '付款失敗'
            instance.simple_status = 2
        instance.ecpay_data = json.dumps(request.data)
        instance.payment_type = request.data.get('PaymentType')
        instance.save()
        return Response('ok')

    @action(methods=['POST'], detail=False, authentication_classes=[], permission_classes=[])
    def payment_info_url(self, request, *args, **kwargs):
        """payment info return url"""
        logger.info('payment info url: %s', request.data['MerchantTradeNo'])
        logger.info('PaymentType: %s', request.data['PaymentType'])
        logger.info('RtnCode: %s', request.data['RtnCode'])
        instance = serializers.Order.objects.filter(order_number=request.data['MerchantTradeNo'][:-2]).first()
        if not instance:
            print('no return instance:', request.data['MerchantTradeNo'])
        if int(request.data['RtnCode']) == 2 or int(request.data['RtnCode']) == 10100073:
            instance.take_number = 1
            instance.simple_status_display = '取號成功'
            instance.simple_status = 3
        else:
            instance.simple_status_display = '取號失敗'
            instance.simple_status = 4
            instance.take_number = 0
            logger.warning('取號失敗: %s', request.data['RtnCode'])
        instance.ecpay_data = json.dumps(request.data)
        instance.payment_type = request.data.get('PaymentType')
        instance.save()
        return Response('ok')

    @action(methods=['POST'], detail=False)
    def shipping(self, request, *args, **kwargs):
        sub_type = request.data['store_type']
        memberstore_id = request.data['memberstore_id']
        memberstore = serializers.MemberStore.objects.get(pk=memberstore_id)
        request.data['address'] = memberstore.address
        store_id = memberstore.store_id
        request.data['store_id'] = store_id
        del request.data['memberstore_id']
        with transaction.atomic():
            self.update_request(request)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            self.reward_process(serializer.instance)
        ecpay.shipping(sub_type, store_id, serializer.instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['POST'], detail=False, authentication_classes=[], permission_classes=[])
    def shipping_return_url(self, request, *args, **kwargs):
        instance = serializers.Order.objects.filter(order_number=request.data['MerchantTradeNo']).first()
        instance.shipping_status = request.data['RtnCode']
        instance.all_pay_logistics_id = request.data['AllPayLogisticsID']
        display = shipping_map.shipping_mapping.get(str(instance.shipping_status))
        if display:
            instance.simple_status_display = display
        instance.save()
        return Response('ok')

    @action(methods=['POST'], detail=False, authentication_classes=[], permission_classes=[])
    def map_return_url(self, request, *ars, **kwargs):
        logger.info('get map_return_url!!!')
        member_id, callback_url = request.data['ExtraData'].split('###')
        member = Member.objects.get(pk=member_id)
        sub_type = request.data['LogisticsSubType']
        if 'C2C' in sub_type:
            sub_type = sub_type.strip('C2C')
        data = dict(
            member=member.id,
            sub_type=sub_type,
            store_id=request.data['CVSStoreID'],
            store_name=request.data['CVSStoreName'],
            address=request.data['CVSAddress'],
            phone=request.data['CVSTelephone'] or None,
        )
        logger.info('map_return_url: %s', data)
        memberstore = MemberStore.objects.filter(sub_type=sub_type).filter(store_id=data['store_id'])
        if memberstore.count():
            return HttpResponseRedirect(callback_url)
        serializer = serializers.MemberStoreSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return HttpResponseRedirect(callback_url)

    @action(methods=['POST'], detail=False)
    def chosse_map(self, request, *ars, **kwargs):
        # todo 要讓api 頁面測試 還有問題
        sub_type = request.data['sub_type']
        callback_url = request.data['callback_url']
        logger.info('chose_map: %s %s', sub_type, callback_url)
        html = ecpay.create_shipping_map(sub_type, self.request.user.id, callback_url)
        return Response(dict(html=html))


@router_url('banner')
class BannerViewSet(UpdateCache, MyMixin):
    queryset = serializers.Banner.objects.all()
    serializer_class = serializers.BannerSerializer
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [(permissions.ReadAuthenticated | permissions.BannerManagerEditPermission)]
    prefix_key = 'banner'

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [(permissions.ReadAuthenticated | permissions.BannerManagerEditPermission),
                                  permissions.BannerReadAuthenticated]
            return [permission() for permission in permission_classes]

        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        now = timezone.now().date()
        if not isinstance(self.request.user, serializers.Manager):
            queryset = queryset.filter(
                Q(status=True) & (Q(display_type=True) | (Q(start_time__lte=now) & Q(end_time__gt=now))))
        return queryset


@router_url('file')
class FileViewSet(MyMixin):
    queryset = serializers.File.objects.all()
    serializer_class = serializers.FileSerializer
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = []
    permission_classes = []
    __doc__ = docs.file


def get_urls():
    urls = router.get_urls()
    for nested_router in nested_routers:
        urls += nested_router.get_urls()
    return urls


@router_url('permission')
class PermissionViewSet(MyMixin):
    serializer_class = PermissionSerializer
    queryset = serializers.Permission.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [
        permissions.RoleAuthenticated
    ]
    __doc__ = docs.permission


@router_url('manager')
class ManagerViewSet(MyMixin):
    serializer_class = ManagerSerializer
    queryset = serializers.Manager.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.ManagerAuthenticated]
    __doc__ = docs.manager

    def get_serializer_class(self):
        serializer_class = self.serializer_class
        if self.action == 'login':
            serializer_class = serializers.ManagerLoginSerializer
        return serializer_class

    @action(methods=['POST'], detail=False,
            authentication_classes=[],
            permission_classes=[],
            )
    def login(self, request, *args, **kwargs):
        # for test ，problem
        data = request.data
        raw_password = data['password']
        del data['password']
        try:
            user = serializers.Manager.objects.filter(status=True).get(**data)
        except Exception as e:
            return Response(data='帳號或密碼錯誤', status=403)
        if not user.check_password(raw_password):
            return Response(data='帳號或密碼錯誤', status=403)
        token, created = serializers.AdminTokens.objects.get_or_create(user=user)
        return Response({'token': token.key})

    @action(methods=['POST'], detail=False, url_path='logout',
            serializer_class=serializers.serializers.Serializer,
            permission_classes=(),
            )
    def logout(self, request, *args, **kwargs):
        request.auth.delete()
        return Response({'msg': 'success'})

    @action(methods=['GET'], detail=False,
            authentication_classes=[TokenAuthentication],
            permission_classes=[],
            )
    def info(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)


@router_url('member')
class MemberViewSet(MyMixin):
    serializer_class = MemberSerializer
    queryset = serializers.Member.objects.all()
    filter_backends = (filters.MemberFilter,)
    pagination_class = LimitOffsetPagination
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.MemberManagerEditPermission,
                          permissions.MemberManagerReadPermission]

    def get_serializer_class(self):
        serializer_class = self.serializer_class
        if self.action == 'login':
            serializer_class = serializers.MemberLoginSerializer
        elif self.action == 'password':
            serializer_class = serializers.MemberPasswordSerializer
        return serializer_class

    def get_authenticators(self):
        authentication_classes = self.authentication_classes
        method = self.request.method.lower()
        self.action = self.action_map.get(method)
        if self.action == 'create':
            authentication_classes = []
        if self.action == 'update':
            authentication_classes = [MangerOrMemberAuthentication]
        return [auth() for auth in authentication_classes]

    def get_permissions(self):
        if self.action in ('create',):
            self.permission_classes = []
        if self.action in ('update',):
            self.permission_classes = [permissions.MemberAuthenticated]
        return [permission() for permission in self.permission_classes]

    @action(methods=['POST'], detail=False, authentication_classes=[], permission_classes=[])
    def register(self, request, *args, **kwargs):
        host = request.data.get('host')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        send_mail(
            subject='【 會員驗證 】EZGO - 汴利購會員驗證信',
            tomail=serializer.instance.account,
            part_content='請點擊下列網址進行信箱驗證',
            tourl=f'{host}/register-validate/{serializer.instance.validate_code}'
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(methods=['POST'], detail=False, authentication_classes=[], permission_classes=[])
    def register_resend(self, request, *args, **kwargs):
        """
        如果註冊超過時間 太晚收信
        則用該validate_code 去重新寄信一次
        """
        host = request.data.get('host')
        validate_code = request.data.get('validate_code')
        instance = get_object_or_404(serializers.Member.objects.filter(validate_code=validate_code))
        instance.set_validate_code()
        instance.save()
        send_mail(
            subject='【 會員驗證 】EZGO - 汴利購會員驗證信',
            tomail=instance.account,
            part_content='請點擊下列網址進行信箱驗證',
            tourl=f'{host}/register-validate/{instance.validate_code}'
        )

        return Response(dict(msg='ok'))

    @action(methods=['POST'], detail=False, authentication_classes=[], permission_classes=[])
    def register_validate(self, request, *args, **kwargs):
        """
        for registe validate
        code:
        -> 1: 註冊成功
        -> 2: 已經驗證過
        -> 3: 已經過期
        -> 4: 找不到該user
        """
        validate_code = request.data.get('validate_code')
        now = timezone.now()
        queryset = serializers.Member.objects.filter(
            validate_code=validate_code,
            # expire_datetime__gte=now,
            # validate=False,
        )
        if queryset.count():
            instance = queryset.first()
            if instance.validate:
                return Response(dict(msg='已經驗證過', code=2), status=200)
            if instance.expire_datetime < now:
                return Response(dict(msg='已經過期', code=3), status=200)

            instance.validate = True
            instance.save()
            return Response(dict(msg='註冊成功', code=1), status=200)
        else:
            return Response(dict(msg='找不到該user', code=4), status=200)

    @action(methods=['POST'], detail=False,
            authentication_classes=[],
            permission_classes=[],
            )
    def login(self, request, *args, **kwargs):
        # for test ，problem
        data = request.data.copy()
        raw_password = data['password']
        del data['password']
        try:
            user = serializers.Member.objects.filter(status=True).get(**data)
        except Exception as e:
            return Response(data='帳號或密碼錯誤', status=403)
        if not user.check_password(raw_password):
            return Response(data='帳號或密碼錯誤', status=403)
        token, created = serializers.MemberTokens.objects.get_or_create(user=user)
        response = Response({'token': token.key})
        # response.set_cookie('token', token.key)
        return response

    @action(methods=['POST'], detail=False, url_path='logout',
            serializer_class=serializers.serializers.Serializer,
            permission_classes=(),
            authentication_classes=[MemberCheckAuthentication]
            )
    def logout(self, request, *args, **kwargs):
        request.auth.delete()
        response = Response({'msg': 'success'})
        # response.set_cookie('token', None)
        return response

    @action(methods=['GET'], detail=False,
            authentication_classes=[MemberCheckAuthentication],
            permission_classes=[],
            )
    def info(self, request, *args, **kwargs):
        """
        record_info:
        目前獎勵金
        目前獎勵金 最近一筆資訊(金額, 到期 year, month, day)
        待生效獎勵金
        待生效獎勵金 最近一筆資訊(金額, 到期 year, month, day)
        生效日期 n 天
        """
        user = request.user
        if isinstance(request.user, Member):
            serializer = self.get_serializer(user)
            # 生效日期 n 天
            still_day = Reward.objects.first().still_day

            instance = RewardRecord.objects.filter(member=user).first()
            total_point = 0 if not instance else instance.total_point
            record = dict(
                total_point=total_point,
                last_point=0 if not instance else instance.point,
                year=None if not instance else instance.end_date.year if instance.end_date else None,
                month=None if not instance else instance.end_date.month if instance.end_date else None,
                day=None if not instance else instance.end_date.day if instance.end_date else None,
            )

            queryset = RewardRecordTemp.objects.filter(member=user).all()
            instance = queryset.first()
            total_point = 0
            for el in queryset:
                total_point += el.point
            record_temp = dict(
                total_point=total_point,
                last_point=0 if not instance else instance.point,
                year=None if not instance else instance.end_date.year,
                month=None if not instance else instance.end_date.month,
                day=None if not instance else instance.end_date.day,
            )
            record_info = dict(
                record=record,
                record_temp=record_temp,
                still_day=still_day,
            )

            return Response(dict(record_info=record_info, **serializer.data))
        else:
            return Response(dict())

    @action(methods=['POST'], detail=False, authentication_classes=[], permission_classes=[])
    def validate_expired(self, request, *args, **kwargs):
        """
        for registe validate
        """
        # todo missing test case
        validate_code = request.data.get('validate_code')
        now = datetime.datetime.now()
        queryset = serializers.Member.objects.filter(
            validate_code=validate_code,
            expire_datetime__gte=now,
        )
        if queryset.count():
            return Response(dict(msg='ok'), status=200)
        else:
            return Response(dict(msg='expired'), status=400)

    @action(methods=['POST'], detail=False,
            authentication_classes=[],
            permission_classes=[],
            )
    def forgotpassword(self, request, *args, **kwargs):
        # todo missing test case
        account = request.data.get('account')
        host = request.data.get('host')
        try:
            instance = serializers.Member.objects.get(account=account)
            instance.set_validate_code()
            instance.save()
        except Exception as e:
            error = dict()
            error['account'] = ['查無此帳號']
            raise serializers.serializers.ValidationError(error)

        send_mail(
            subject='【 重設密碼 】EZGO - 汴利購會員重設密碼信',
            tomail=account,
            part_content='請點擊下列網址重設新密碼',
            tourl=f'{host}/set-password/{instance.validate_code}'
        )

        return Response(dict(msg='ok'))

    @action(methods=['POST'], detail=False,
            authentication_classes=[],
            permission_classes=[],
            serializer_class=serializers.MemberForgotPasswordToSrtSerializer
            )
    def forgotpassword_setpassword(self, request, *args, **kwargs):
        # todo missing test case
        kwargs['partial'] = True
        partial = kwargs.pop('partial', True)
        validate_code = request.data.get('validate_code')
        now = datetime.datetime.now()
        queryset = serializers.Member.objects.filter(
            validate_code=validate_code,
            expire_datetime__gte=now,
        )
        if not queryset.count():
            return Response(dict(msg='expired'), status=400)
        instance = queryset.first()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def get_object(self):
        """
        客製化的 Member 不能要其他人資料
        """
        if self.action in ['self_update', 'password']:
            return self.request.user
        return super().get_object()

    @action(methods=['PUT'], detail=False,
            authentication_classes=[MemberAuthentication],
            permission_classes=[],
            )
    def self_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        partial = kwargs.pop('partial', True)
        host = request.data.get('host')
        instance = self.get_object()
        account = request.data.get('account')
        if account and account != instance.account:
            instance.validate = False
            instance.set_validate_code()
            instance.save()
            send_mail(
                subject='【 會員驗證 】EZGO - 汴利購會員驗證信',
                tomail=account,
                part_content='請點擊下列網址進行信箱驗證',
                tourl=f'{host}/register-validate/{instance.validate_code}'
            )
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    @action(methods=['PUT'], detail=False,
            authentication_classes=[MemberAuthentication],
            permission_classes=[],
            serializer_class=serializers.MemberPasswordSerializer
            )
    def password(self, request, *args, **kwargs):
        """
        get_object 取得自己
        """
        return self.update(request, *args, **kwargs)

    @action(methods=['POST'], detail=False,
            authentication_classes=[MemberAuthentication],
            serializer_class=serializers.MemberAddressSerializer,
            permission_classes=(),
            )
    def memberaddress(self, request, *args, **kwargs):
        data = request.data.copy()
        data['member'] = request.user.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        if not serializer.instance.member.default_memberaddress:
            serializer.instance.member.default_memberaddress = serializer.instance
            serializer.instance.member.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(methods=['GET'], detail=False,
            authentication_classes=[MemberCheckAuthentication],
            permission_classes=[],
            serializer_class=serializers.MemberWishSerializer
            )
    def memberwish(self, request, *args, **kwargs):
        user = request.user
        if isinstance(user, Member):
            serializer = self.get_serializer(user.memberwish.all(), many=True)
            return Response(serializer.data)
        else:
            return Response([])

    @action(methods=['GET'], detail=False,
            authentication_classes=[MemberAuthentication],
            permission_classes=[],
            serializer_class=serializers.OrderSerializer
            )
    def order(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(user.order.all(), many=True)
        return Response(serializer.data)


@router_url('memberwish')
class MemberWishViewSet(CreateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = serializers.MemberWish.objects.all()
    serializer_class = serializers.MemberWishSerializer
    authentication_classes = [MemberAuthentication]
    permission_classes = []

    def create(self, request, *args, **kwargs):
        queryset = serializers.MemberWish.objects.filter(member=request.user, product=request.data.get('product'))
        if queryset.count():
            queryset.delete()
            return Response(dict(msg='已經刪除商品收藏', status='delete'))
        else:
            super().create(request, *args, **kwargs)
            return Response(dict(msg='已經加到商品收藏', status='create'))


@router_url('memberaddress')
class MemberAddressViewSet(UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = serializers.MemberAddress.objects.all()
    serializer_class = serializers.MemberAddressSerializer
    authentication_classes = [MemberAuthentication]
    permission_classes = []


@router_url('category')
class CategoryViewSet(MyMixin, UpdateCache):
    queryset = serializers.Category.objects.all()
    serializer_class = serializers.CategorySerializer
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [permissions.CategoryAuthenticated]
    prefix_key = 'category'

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.queryset
        if self.action == 'list':
            queryset = serializers.Category.objects.filter(main_category=None)
        return queryset


@router_url('tag')
class TagProductViewSet(MyMixin, UpdateCache):
    queryset = serializers.Tag.objects.all()
    serializer_class = serializers.TagSerializer
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [permissions.TagAuthenticated]
    prefix_key = 'tag'

    # def get_queryset(self):
    #     queryset = super().get_queryset()
    #     queryset = self.get_serializer_class().setup_eager_loading(queryset)
    #     return queryset


@router_url('taglist')
class TagListViewSet(ListModelMixin, viewsets.GenericViewSet):
    queryset = serializers.Tag.objects.all()
    serializer_class = serializers.TagListSerializer
    authentication_classes = [MemberCheckAuthentication]

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


@router_url('tagimage')
class TagImageViewSet(MyMixin):
    queryset = serializers.TagImage.objects.all()
    serializer_class = serializers.TagImageSerializer
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [permissions.TagAuthenticated]


@router_url('brand')
class BrandViewSet(MyMixin, UpdateCache):
    queryset = serializers.Brand.objects.all()
    serializer_class = serializers.BrandSerializer
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [permissions.BrandAuthenticated]
    prefix_key = 'brand'

    def list(self, request, *args, **kwargs):
        from collections import defaultdict
        import string
        response = super().list(request, *args, **kwargs)
        data = response.data
        dct = defaultdict(list)
        ret = []
        i = 0
        for el in data:
            name = el['en_name']
            key = name[0].upper()
            if key in string.digits:
                key = '0-9'
            dct[key].append(el)
        for k in sorted(dct.keys()):
            i += 1
            children = []
            for el in sorted(dct[k], key=lambda d: d['en_name'].upper()):
                i += 1
                el['fake_id'] = i
                children.append(el)
            ret.append(dict(
                name=k,
                fake_id=i,
                children=children
            ))
        response.data = ret
        return response

    def create(self, request, *args, **kwargs):
        brand = Brand.original_objects.filter(en_name=request.data['en_name']).delete()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


@router_url('product')
class ProductViewSet(MyMixin, UpdateCache):
    queryset = serializers.Product.objects.select_related('brand'). \
        prefetch_related('tag'). \
        prefetch_related('category'). \
        prefetch_related('productimages'). \
        prefetch_related('specifications').prefetch_related('specifications_detail').all()
    serializer_class = serializers.ProductSerializer
    filter_backends = (filters.ProductFilter,)
    pagination_class = LimitOffsetPagination
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [(permissions.ReadAuthenticated | permissions.ProductManagerEditPermission)]
    prefix_key = 'product'

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [(permissions.ReadAuthenticated | permissions.ProductManagerEditPermission),
                                  permissions.ProductReadAuthenticated]
            return [permission() for permission in permission_classes]

        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        if (self.action == 'list' or self.action == 'index_page') and not isinstance(self.request.user, Manager):
            queryset = queryset.filter(status=True)
        return queryset

    @action(methods=['GET'], detail=False, permission_classes=[], authentication_classes=[])
    def index_page(self, request, *args, **kwargs):
        # new product 4
        queryset = self.filter_queryset(self.get_queryset())
        new_products = self.get_data(queryset[:4])
        # hot product 8
        queryset = self.filter_queryset(self.get_queryset())
        queryset.order_by('-order_count')
        hot_products = self.get_data(queryset[:8])
        # alltag 8
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(tag__isnull=False)
        alltag_products = self.get_data(queryset[:8])
        # tags 8
        tags_queryset = serializers.Tag.objects.all()
        tags = dict()
        for tag in tags_queryset:
            queryset = self.filter_queryset(self.get_queryset())
            queryset = queryset.filter(tag=tag)
            tags[tag.id] = self.get_data(queryset[:8])
        ret = dict(new_products=new_products, hot_products=hot_products, alltag_products=alltag_products, tags=tags)

        return Response(ret)

    def get_data(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return serializer.data

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        user = request.user
        page = self.paginate_queryset(queryset)
        if page is not None:
            q = self.get_queryset()
            min_price = queryset.aggregate(min_price=Min('specifications_detail__price'))['min_price']
            max_price = queryset.aggregate(max_price=Max('specifications_detail__price'))['max_price']
            serializer = self.get_serializer(page, many=True)
            ret = self.get_paginated_response(serializer.data)
            ret.data['min_price'] = min_price
            ret.data['max_price'] = max_price
            return ret

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@router_url('specificationdetail')
class ProductViewSet(UpdateModelMixin, viewsets.GenericViewSet):
    queryset = serializers.SpecificationDetail.objects.all()
    serializer_class = serializers.SpecificationDetailSerializer
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [(permissions.ReadAuthenticated | permissions.ProductManagerEditPermission)]


@router_url('product', prefix='tag')
class ProductListViewSet(NestedViewSetBase, ListModelMixin, viewsets.GenericViewSet):
    parent_model = 'tag'
    serializer_class = ProductListSerializer
    queryset = serializers.Product.objects.select_related('brand').select_related('category'). \
        select_related('tag'). \
        prefetch_related('productimages').prefetch_related('specifications').all()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = request.user
        if self.action == 'list' and not isinstance(user, Manager):
            queryset = queryset.filter(status=True).all()
        return queryset


@router_url('cart')
class CartViewSet(MyMixin):
    queryset = serializers.Cart.objects.select_related('product').select_related('specification_detail'). \
        prefetch_related('product__productimages').all()
    serializer_class = serializers.CartSerializer
    permission_classes = []
    authentication_classes = [MangerOrMemberAuthentication]

    def create(self, request, *args, **kwargs):
        instance = serializers.Cart.objects.filter(
            member=request.user, product=request.data.get('product'),
            specification_detail=request.data.get('specification_detail')).first()
        if not instance:
            return super().create(request, *args, **kwargs)
        else:
            instance.quantity += int(request.data.get('quantity', 0))
            instance.save()
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        if self.action in ['list', 'retrieve']:
            serializer_class = serializers.CartResposneSerializer
        return serializer_class

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action in ['list', 'retrieve', 'total', 'count']:
            queryset = queryset.filter(member=self.request.user)
        return queryset

    @action(methods=['GET'], detail=False, authentication_classes=[MemberCheckAuthentication])
    def count(self, request, *args, **kwargs):
        from django.contrib.auth.models import AnonymousUser
        count = 0
        if not isinstance(request.user, AnonymousUser):
            queryset = self.filter_queryset(self.get_queryset())
            for el in queryset:
                count += el.quantity
        return Response(dict(count=int(count)))

    @action(methods=['GET'], detail=False, authentication_classes=[MemberCheckAuthentication])
    def total(self, request, *args, **kwargs):
        from django.contrib.auth.models import AnonymousUser
        total = 0
        if not isinstance(request.user, AnonymousUser):
            queryset = self.filter_queryset(self.get_queryset())
            for cart in queryset:
                total += cart.specification_detail.price * cart.quantity
        return Response(dict(total=int(total)))

    def list(self, request, *args, **kwargs):
        # 用cookie 判斷 如果有給資料一樣給他cart 資料
        if isinstance(request.user, AnonymousUser):
            # get cart
            import urllib.parse
            cart = request.COOKIES.get('cart')
            if cart:
                cart = json.loads(urllib.parse.unquote(request.COOKIES.get('cart')))
            cart = cart or request.query_params.get('cart')
            if isinstance(cart, str):
                cart = json.loads(cart)
            ret = []
            if not cart:
                return Response(ret)
            for c in cart:
                # 防呆前端傳 None
                if not c['specification_detail']:
                    continue
                product = serializers.ProductForCartSerializer(instance=Product.objects.get(pk=c['product']))
                specification_detail = serializers.SpecificationDetailSerializer(
                    instance=SpecificationDetail.objects.get(pk=c['specification_detail']))
                ret.append(dict(
                    specification_detail=specification_detail.data,
                    product=product.data,
                    spec1_name=product.data['level1_title'],
                    spec2_name=product.data['level2_title'],
                    quantity=c['quantity'],
                ))
            return Response(ret)
        return super().list(request, *args, **kwargs)


@router_url('memberstore')
class MemberStoreViewSet(CreateModelMixin, ListModelMixin, DestroyModelMixin, viewsets.GenericViewSet):
    queryset = serializers.MemberStore.objects.all()
    serializer_class = serializers.MemberStoreSerializer
    authentication_classes = [MemberAuthentication]
    permission_classes = []

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(member=self.request.user)\



@router_url('blacklistrecord')
class BlackListRecordViewSet(CreateModelMixin, viewsets.GenericViewSet):
    queryset = serializers.BlacklistRecord.objects.all()
    serializer_class = serializers.BlackListRecordSerializer
    authentication_classes = [MangerOrMemberAuthentication]
    permission_classes = [(
            permissions.MemberAuthenticated | permissions.MemberManagerEditPermission & permissions.MemberManagerReadPermission)]


@router_url('productquitshot')
class ProductQuitShotViewSet(MyMixin):
    queryset = serializers.ProductQuitShot.objects.all()
    serializer_class = serializers.ProductQuitShotSerializer
    authentication_classes = [MemberAuthentication]
    permission_classes = []


@router_url('freeshipping')
class FreeShippingViewSet(UpdateModelMixin, ListModelMixin, viewsets.GenericViewSet):
    queryset = serializers.FreeShipping.objects.all()
    serializer_class = serializers.FreeShippingSerializer
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [(permissions.ReadAuthenticated | permissions.CouponManagerEditPermission)]

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [(permissions.ReadAuthenticated | permissions.CouponManagerEditPermission),
                                  permissions.CouponReadAuthenticated]
            return [permission() for permission in permission_classes]

        return super().get_permissions()

    def get_queryset(self):
        ret = super().get_queryset()
        if not isinstance(self.request.user, Manager):
            ret = ret.filter(enable=True)
        return ret


@router_url('coupon')
class CouponViewSet(MyMixin, UpdateCache):
    queryset = serializers.Coupon.objects.all()
    serializer_class = serializers.CouponSerializer
    filter_backends = (filters.CouponFilter,)
    authentication_classes = [MangerOrMemberAuthentication]
    permission_classes = [(permissions.ReadAuthenticated | permissions.CouponManagerEditPermission)]
    prefix_key = 'coupon'

    def get_queryset(self):
        """
        找沒有限定會員的或者是你本身是屬於該限定會員的coupon
        """
        queryset = super().get_queryset()
        if self.action == 'retrieve' and not isinstance(self.request.user, Manager):
            queryset = queryset.filter(Q(has_member_list=False) | Q(has_member_list=True, member=self.request.user))
        if self.action == 'list' and not isinstance(self.request.user, Manager):
            queryset = queryset.filter(has_member_list=False)
        return queryset

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [(permissions.ReadAuthenticated | permissions.CouponManagerEditPermission),
                                  permissions.CouponReadAuthenticated]
            return [permission() for permission in permission_classes]

        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        instance = queryset.filter(discount_code=self.kwargs.get('pk')).first()
        if not instance:
            return Response()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@router_url('rewardrecord')
class RewardRecordViewSet(CreateModelMixin, ListModelMixin, viewsets.GenericViewSet):
    queryset = serializers.RewardRecord.objects.all()
    serializer_class = serializers.RewardRecordSerializer
    pagination_class = LimitOffsetPagination
    authentication_classes = [MangerOrMemberAuthentication]
    permission_classes = [(permissions.ReadAuthenticated | permissions.CouponManagerEditPermission)]

    def get_permissions(self):
        if self.action == 'list':
            return []
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        if isinstance(request.user, AnonymousUser):
            return Response([])
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        確認是不是統一要改變日期
        """
        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            serializer.instance.check_config()
            headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if isinstance(user, Member) and self.action == 'list':
            queryset = queryset.filter(member=user)
        return queryset


@router_url('rewardrecordtemp')
class RewardRecordTempViewSet(UpdateModelMixin, viewsets.GenericViewSet):
    queryset = serializers.RewardRecordTemp.objects.all()
    serializer_class = serializers.RewardRecordTempSerializer
    pagination_class = LimitOffsetPagination
    authentication_classes = [MangerOrMemberAuthentication]
    permission_classes = [(permissions.ReadAuthenticated | permissions.CouponManagerEditPermission)]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if isinstance(user, Member) and self.action == 'list':
            queryset = queryset.filter(member=user)
        return queryset


@router_url('reward')
class RewardViewSet(CreateModelMixin, ListModelMixin, UpdateModelMixin, viewsets.GenericViewSet):
    queryset = serializers.Reward.objects.all()
    serializer_class = serializers.RewardSerializer
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [(permissions.ReadAuthenticated | permissions.CouponManagerEditPermission)]

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [(permissions.ReadAuthenticated | permissions.CouponManagerEditPermission),
                                  permissions.CouponReadAuthenticated]
            return [permission() for permission in permission_classes]

        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset.first(), )
        return Response(serializer.data)


@router_url('membertoken')
class MemberTokenViewSet(MyMixin):
    queryset = serializers.MemberTokens.objects.all()
    serializer_class = serializers.MemberSerializer
    authentication_classes = [MemberCheckAuthentication]
    permission_classes = []

    def list(self, request, *args, **kwargs):
        ret = dict(token=isinstance(request.user, serializers.Member))
        ret['msg'] = request.META.get("HTTP_AUTHORIZATION")
        return Response(ret)


class PriceHandler:
    def __init__(self):
        self.url = 'https://rate.bot.com.tw/cr?Lang=zh-TW'
        self.format = '%Y-%m-%dT%H:%M:%S'

    def crawl_data(self):
        r = None
        for i in range(10):
            try:
                r = requests.get(self.url)
                break
            except Exception as e:
                pass
        else:
            return
        dom = pq(r.text)
        dct = dict(tw=1, en=1 / float(dom('td.text-right').eq(0).text()),
                   t=datetime.datetime.now().strftime(self.format))
        return dct


@router_url('price')
class PriceViewSet(MyMixin, UpdateCache):
    queryset = serializers.MemberTokens.objects.all()
    serializer_class = serializers.serializers.Serializer
    authentication_classes = []
    permission_classes = []
    prefix_key = 'price'

    def list(self, request, *args, **kwargs):
        ret = PriceHandler().crawl_data()
        return Response(ret)


@router_url('cache')
class CacheViewSet(MyMixin):
    queryset = serializers.MemberTokens.objects.all()
    serializer_class = serializers.serializers.Serializer
    authentication_classes = []
    permission_classes = []

    def retrieve(self, request, *args, **kwargs):
        super().retrieve()

    def list(self, request, *args, **kwargs):
        ret = pickle_redis.get_data('cache')
        return Response(ret)


@router_url('configsetting')
class ConfigSettingViewSet(UpdateCache, UpdateModelMixin, ListModelMixin, viewsets.GenericViewSet):
    queryset = serializers.ConfigSetting.objects.all()
    serializer_class = serializers.ConfigSettingSerializer
    authentication_classes = []
    permission_classes = []

    def list(self, request, *args, **kwargs):
        config = get_config()
        return Response(config)

    def update(self, request, *args, **kwargs):
        import subprocess
        # todo 如果更新 update redis
        ret = super().update(request, *args, **kwargs)
        key = 'configsetting'
        pickle_redis.remove_data(key)
        config = get_config()
        with open('./config.json', 'w') as f:
            f.write(json.dumps(config))
        subprocess.call('./init.sh')
        return ret


@router_url('country')
class CountryViewSet(ListModelMixin, viewsets.GenericViewSet):
    queryset = serializers.Country.objects.all()
    serializer_class = serializers.serializers
    authentication_classes = []
    permission_classes = []

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        ret = []
        for el in queryset:
            ret.append(el.name)
        return Response(ret)


def get_category_ids_mapping():
    queryset = Category.objects.all()
    ret = defaultdict(list)
    for el in queryset:
        if el.main_category:
            ret[el.main_category.id].append(el.id)
    delete_ids = []
    keys = ret.keys()
    for main_category_id in ret:
        target_list = ret[main_category_id]
        a = [1, 2, ]
        delete_ids = []
        for _id in target_list:
            if _id in keys:
                delete_ids.append(_id)
                target_list.extend(ret[_id])
        for _id in delete_ids:
            target_list.remove(_id)
    return ret


@router_url('activity')
class ActivityViewSet(MyMixin):
    queryset = serializers.Activity.objects.all()
    serializer_class = serializers.ActivitySerializer
    filter_backends = (filters.ActivityFilter,)
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [(permissions.ReadAuthenticated | permissions.CouponManagerEditPermission)]

    @action(methods=['POST'], detail=False)
    def category(self, request, *args, **kwargs):
        # todo 如國要做好 rest api 那邊應該要顯示 接收什麼參數.... etc
        ids = request.data['ids']
        activity_id = request.data['activity']
        category_ids_mapping = get_category_ids_mapping()
        new_ids = []
        for _id in ids:
            if _id in category_ids_mapping:
                new_ids.extend(category_ids_mapping[_id])
            else:
                new_ids.append(_id)
        products = Product.objects.filter(category__in=new_ids)
        with transaction.atomic():
            for product in products:
                product.activity_id = activity_id
        return Response(dict(msg='ok'), status=status.HTTP_201_CREATED)


@router_url('exportorder')
class ExportOrderViewSet(ListModelMixin, viewsets.GenericViewSet):
    queryset = serializers.Order.objects.all()
    serializer_class = serializers.OrderSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = (filters.OrderFilter,)
    authentication_classes = [MangerOrMemberAuthentication]
    permission_classes = [(
            permissions.OrderAuthenticated | permissions.OrderManagerEditPermission & permissions.OrderManagerReadPermission)]

    def list(self, request, *args, **kwargs):
        def get_store(el):
            if not el['to_store']:
                return '宅配'
            mapping = {
                'FAMI': '全家',
                'UNIMART': '7-11',
                'HILIFE': '萊爾富',
                'FAMIC2C': '全家',
                'UNIMARTC2C': '7-11',
                'HILIFEC2C': '萊爾富',
            }
            return f'超商( {mapping[el["store_type"]]} )'

        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        ret = []
        for el in serializer.data:
            dct = {
                '訂單編號': el['order_number'],
                '收件人': el['shipping_name'],
                '訂單金額': el['total_price'],
                '物流方式': get_store(el),
                '店名': el['store_name'],
                '訂單日期': el['created_at'],
                '訂單狀態': el['simple_status_display'],
                '當前貨態': el['shipping_status_display'],
            }
            ret.append(dct)
        df = pd.DataFrame(data=ret)
        # file_name = f'{str(uuid.uuid4())[:10]}.csv'
        file_name = f'訂單資訊.csv'
        df.to_csv(f'./media/{file_name}')
        return Response(data=dict(
            file_name=file_name,
        ))


@router_url('exportmember')
class ExportMemberViewSet(ListModelMixin, viewsets.GenericViewSet):
    queryset = serializers.Member.objects.all()
    serializer_class = serializers.MemberSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = (filters.MemberFilter,)
    authentication_classes = [MangerOrMemberAuthentication]
    permission_classes = [(
            permissions.MemberAuthenticated | permissions.MemberManagerEditPermission & permissions.MemberManagerReadPermission)]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        ret = []
        for el in serializer.data:
            dct = {
                '會員編號': el['member_number'],
                '姓名': el['name'],
                '會員帳號': el['account'],
                '註冊時間': el['join_at'],
                '回饋點數': el['returns'],
                '消費次數': el['order_count'],
                '消費金額': el['pay_total'],
                '狀態': '啟用中' if el['status'] else '停用中',
            }
            ret.append(dct)
        df = pd.DataFrame(data=ret)
        # file_name = f'{str(uuid.uuid4())[:10]}.csv'
        file_name = f'會員資訊.csv'
        df.to_csv(f'./media/{file_name}')
        return Response(data=dict(
            file_name=file_name,
        ))
