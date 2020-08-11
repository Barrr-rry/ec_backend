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
                     RewardRecordTemp, Activity, BlacklistRecord, MemberSpec, HomeActivity,
                     ProductImage, Cart, ProductQuitShot, TagImage, FreeShipping, Coupon, MemberStore)
from .serializers import (BannerSerializer, FileSerializer, PermissionSerializer, ManagerSerializer,
                          ManagerLoginSerializer, HomeActivitySerializer,
                          MemberSerializer, CategorySerializer, TagSerializer, BrandSerializer, ProductSerializer,
                          CartSerializer, ProductQuitShotSerializer, TagImageSerializer, TagListSerializer,
                          ProductListSerializer, FreeShippingSerializer, CouponSerializer, MemberLoginSerializer,
                          MemberPasswordSerializer, BlackListRecordSerializer, MemberGetEmailSerializer)
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
from log import logger, ecpay_loggger

from django.utils.decorators import method_decorator
from django.db.models import Q, F
from .util import pickle_redis, get_config
import uuid
from django.db.models import Max, Min
from collections import defaultdict
import pandas as pd
import uuid
from django.db.models import Q, Sum, Count
from django.db.models.functions import Coalesce

router = routers.DefaultRouter()
nested_routers = []
orderdct = OrderedDict()


class UpdateCache:
    """
    有些rest api 需要cache
    除了get 資料以外 每一次 都會更新 該資料的uuid
    前端對到了發現如果不一樣的話 就要重新要資料不能抓cache的資料
    """
    prefix_key = None

    def update(self, *args, **kwargs):
        # 資料異動 更新cache uuid
        self.cache_process()
        return super().update(*args, **kwargs)

    def create(self, *args, **kwargs):
        # 資料異動 更新cache uuid
        self.cache_process()
        return super().create(*args, **kwargs)

    def destroy(self, *args, **kwargs):
        # 資料異動 更新cache uuid
        self.cache_process()
        return super().destroy(*args, **kwargs)

    def cache_process(self):
        if not self.prefix_key:
            return
        data = pickle_redis.get_data('cache')
        # 將這些table key 加上 uuid 做之後的判斷 是不是同一組
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
        # default 的update partial 是False 就是代表必須要全部更新 但是很長我們只想要更新部分的資料 所以取代update 的功能
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
    """
    這樣如果CRUD 都要的話 直接繼承這個 避免上面的update 還要額外繼承
    """


def router_url(url, prefix=None, *args, **kwargs):
    """
    這樣物件 就可以直接註冊urls 網址
    就不用每一個class 還要在urls.py 註冊減少切換的時間
    且不用每次要從路徑找class 也不用切換 好處多多
    寫法仿造Flask
    """

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


"""
viewset 寫法是根據framework
如果function 沒有介紹就是framework 的function
在此不多贅述
要使用人家的套件還是要看一下有什麼東西
ref: https://www.django-rest-framework.org/api-guide/viewsets/
"""


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
        # 如果是會員而不是管理者的話 就只能抓該會員的訂單
        if isinstance(self.request.user, Member):
            queryset.filter(member=self.request.user)
        return queryset

    def update(self, request, *args, **kwargs):
        """
        如果rewmark 更新 就要連更新時間一起更新
        不用updated_at 是因為有可能 沒更新remark 這樣就會抓不到真正的時間了
        """
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
        """
        要針對request 做一些前處理
        :param request: raw request
        :return: product_shot, total_price
        """
        carts = request.user.cart.all()
        product_price = 0
        coupon_discount = 0
        # 這不是被用來存進db 的 所以要把它刪除
        reward_discount = request.data.get('reward_discount', 0)
        if 'reward_discount' in request.data:
            del request.data['reward_discount']
        freeshipping_price = 0
        total_weight = 0
        # 判斷coupon 時間用
        now = datetime.datetime.now()
        # 購物車沒有資料 就代表有問題
        if not carts:
            raise serializers.serializers.ValidationError('no carts')
        product_shot = []
        # 如果 規格含這些文字 則會存入member spec 未來會用到
        spec_size_data = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']
        member_spec = set()
        for cart in carts:
            # 更新商品 order count
            cart.product.order_count += cart.quantity
            cart.product.save()
            spec = cart.specification_detail.level1_spec
            if spec.name in spec_size_data:
                member_spec.add(spec.name)
            # 計算購物車目前的product 價錢 數量 重量等 並且存成product shot
            obj = serializers.ProductSerializer(cart.product).data
            product_price += cart.quantity * cart.specification_detail.price
            obj['specification_detail'] = serializers.SpecificationDetailSerializer(cart.specification_detail).data
            obj['quantity'] = cart.quantity
            total_weight += cart.specification_detail.weight * cart.quantity
            product_shot.append(obj)
        # 清空購物車
        request.user.cart.all().delete()
        # 包含spec_size_data 的規格新增
        for spec_name in member_spec:
            queryset = MemberSpec.objects.filter(member=request.user, name=spec_name)
            if not queryset:
                MemberSpec.objects.create(member=request.user, name=spec_name)

        """
        判斷coupon 是否在時間內以及他是否有使用權限
        如果有使用權限的話計算 coupoon discount
        """
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

        """
        判斷免運費重量是否合理
        以及價錢為多少
        """
        freeshipping_id = request.data.get('freeshipping_id')
        freeshipping = serializers.FreeShipping.objects.get(pk=freeshipping_id)
        if freeshipping.weight >= total_weight:
            if freeshipping_price == 0 or freeshipping_price > freeshipping.price:
                freeshipping_price = freeshipping.price
            if freeshipping.role <= product_price:
                freeshipping_price = 0
        else:
            raise Exception('超出重量')
        # 計算活動折扣金額
        activity_price = self.get_activity_price(carts)
        # 計算總金額
        total_price = product_price + freeshipping_price - activity_price - coupon_discount - reward_discount
        # 更新request 資料 之後要存入db
        request.data['product_shot'] = json.dumps(product_shot)
        request.data['total_price'] = total_price
        request.data['activity_price'] = activity_price
        request.data['freeshipping_price'] = freeshipping_price
        request.data['product_price'] = product_price
        request.data['coupon_price'] = coupon_discount
        request.data['reward_price'] = reward_discount
        request.data['shipping_status'] = 1

        # 每筆訂單更新 會員資料
        member = request.user
        member.gender = request.data.get('gender')
        member.height = request.data.get('height')
        member.weight = request.data.get('weight')
        if member.height and member.weight:
            member.bmi = int(member.weight) / pow((int(member.height) / 100), 2)
        if request.data.get('birthday', None) != 'Invalid date':
            member.birthday = request.data.get('birthday', None)
        member.save()
        return product_shot, total_price

    def get_activity_price(self, carts):
        """
        計算活動折扣
        :param carts: 購物車商品
        :return: 折扣金額
        """
        ret = 0
        in_activity_obj = dict()
        # 計算公式
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
        for key, el in in_activity_obj.items():
            save_count = el['save_count']
            while save_count:
                save_count -= 1
                ret += el['price_list'].pop(0)

        return ret

    @action(methods=['POST'], detail=False)
    def repayment(self, request, *args, **kwargs):
        """
        從該order 重新付款
        取得html form 給前端 讓前端執行submit
        """
        order_id = request.data.get('order_id')
        url = request.data['callback_url']
        lang = request.data.get('lang', '')
        instance = serializers.Order.objects.get(pk=order_id)
        ret = {'html': ecpay.create_html(url, instance, lang=lang)}
        return Response(ret)

    @action(methods=['POST'], detail=False)
    def payment(self, request, *args, **kwargs):
        data = request.data
        # 判斷前端是否有勾選儲存 地址
        if data.get('check_address'):
            user = request.user
            # 如果找不到相同的才要新增
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
        # 取得 付款成功callback url 並且刪掉 無法存進db
        url = data['callback_url']
        del data['callback_url']

        # 更新data store id address
        memberstore_id = data.get('memberstore_id')
        if memberstore_id:
            memberstore = serializers.MemberStore.objects.get(pk=memberstore_id)
            store_id = memberstore.store_id
            data['store_id'] = store_id
            data['address'] = memberstore.address
        with transaction.atomic():
            """
            做的處理 update request 都做好了 serializer 只要直接儲存就好
            """
            self.update_request(request)
            if request.data.get('birthday') == 'Invalid date':
                request.data['birthday'] = None
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
        """
        reward 新增或減少判斷
        """
        # 減少
        instance = RewardRecord.objects.filter(member=order.member).first()
        if instance:
            record = RewardRecord.objects.filter(member=order.member).first()
            rewardrecord = RewardRecord.objects.create(
                member=order.member,
                order=order,
                point=-order.reward_price,
                total_point=instance.total_point - order.reward_price,
                desc=f'購物獎勵金折抵\n（ 訂單編號 : {order.order_number} ）',
                end_date=record.end_date,
            )
        # 新增
        self.to_reward(order)

    def to_reward(self, order):
        # 新增reward
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
        """
        payment return 後端的時候就是來到這邊
        """
        ecpay_loggger.info(f'return url method: {request.stream.method}')
        """payment return url"""
        ecpay_loggger.info(f'return url: {request.data["MerchantTradeNo"]}')
        instance = serializers.Order.objects.filter(order_number=request.data['MerchantTradeNo'][:-2]).first()
        if not instance:
            ecpay_loggger.warning(f'no return instance: {request.data["MerchantTradeNo"]}')
            print('no return instance:', request.data['MerchantTradeNo'])
        if int(request.data['RtnCode']) == 1:
            instance.pay_status = 1
            instance.simple_status_display = '待出貨'
            instance.simple_status = 1
            # 如果是超商付款成功後建立物流
            if instance.to_store:
                ecpay.shipping(instance.store_type, instance.store_id, instance)
        if int(request.data['RtnCode']) == 10100141:
            ecpay_loggger.warning(f'pay fail instance: {request.data["MerchantTradeNo"]}')
            instance.simple_status_display = '付款失敗'
            instance.simple_status = 2
        instance.ecpay_data = json.dumps(request.data)
        instance.payment_type = request.data.get('PaymentType')
        instance.save()
        return Response('ok')

    @action(methods=['POST'], detail=False, authentication_classes=[], permission_classes=[])
    def payment_info_url(self, request, *args, **kwargs):
        """payment info return url"""
        ecpay_loggger.info('payment info url: %s', request.data['MerchantTradeNo'])
        ecpay_loggger.info('PaymentType: %s', request.data['PaymentType'])
        ecpay_loggger.info('RtnCode: %s', request.data['RtnCode'])
        instance = serializers.Order.objects.filter(order_number=request.data['MerchantTradeNo'][:-2]).first()
        if not instance:
            print('no return instance:', request.data['MerchantTradeNo'])
        if int(request.data['RtnCode']) == 2 or int(request.data['RtnCode']) == 10100073:
            instance.take_number = 1
            instance.simple_status_display = '等待付款'
            instance.simple_status = 3
        else:
            instance.simple_status_display = '取號失敗'
            instance.simple_status = 4
            instance.take_number = 0
            ecpay_loggger.warning('取號失敗: %s', request.data['RtnCode'])
        instance.ecpay_data = json.dumps(request.data)
        instance.payment_type = request.data.get('PaymentType')
        instance.save()
        return Response('ok')

    @action(methods=['POST'], detail=False)
    def shipping(self, request, *args, **kwargs):
        """
        純粹物流
        """
        sub_type = request.data['store_type']
        memberstore_id = request.data['memberstore_id']
        memberstore = serializers.MemberStore.objects.get(pk=memberstore_id)
        request.data['address'] = memberstore.address
        store_id = memberstore.store_id
        request.data['store_id'] = store_id
        del request.data['memberstore_id']
        with transaction.atomic():
            """
            物流也是要update 但是做的事情不一樣
            """
            self.update_request(request)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            self.reward_process(serializer.instance)
        ecpay.shipping(sub_type, store_id, serializer.instance)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=['POST'], detail=False, authentication_classes=[], permission_classes=[])
    def shipping_return_url(self, request, *args, **kwargs):
        """
        物流return 的url
        """
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
        """
        取得物流 地圖的return url 當前端選擇哪一個店家 會傳到這個地方
        """
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
        """
        呼叫map 的html form 前端主動submit
        """
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
        """
        list 的permission 不一樣 要單獨
        """
        if self.action == 'list':
            permission_classes = [(permissions.ReadAuthenticated | permissions.BannerManagerEditPermission),
                                  permissions.BannerReadAuthenticated]
            return [permission() for permission in permission_classes]

        return super().get_permissions()

    def get_queryset(self):
        queryset = super().get_queryset()
        now = timezone.now().date()
        # 不是管理員的話 就只抓開始的banner
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
    """
    將router urls 的uels 轉到urls.py
    """
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
        """
        login 的話 切換serializer
        """
        serializer_class = self.serializer_class
        if self.action == 'login':
            serializer_class = serializers.ManagerLoginSerializer
        return serializer_class

    @action(methods=['POST'], detail=False,
            authentication_classes=[],
            permission_classes=[],
            )
    def login(self, request, *args, **kwargs):
        """
        登入判斷
        """
        data = request.data
        # 先判斷帳號
        raw_password = data['password']
        del data['password']
        try:
            user = serializers.Manager.objects.filter(status=True).get(**data)
        except Exception as e:
            return Response(data='帳號或密碼錯誤', status=403)
        # 在判斷密碼
        if not user.check_password(raw_password):
            return Response(data='帳號或密碼錯誤', status=403)
        # 給token
        token, created = serializers.AdminTokens.objects.get_or_create(user=user)
        return Response({'token': token.key})

    @action(methods=['POST'], detail=False, url_path='logout',
            serializer_class=serializers.serializers.Serializer,
            permission_classes=(),
            )
    def logout(self, request, *args, **kwargs):
        """
        刪除token
        """
        request.auth.delete()
        return Response({'msg': 'success'})

    @action(methods=['GET'], detail=False,
            authentication_classes=[TokenAuthentication],
            permission_classes=[],
            )
    def info(self, request, *args, **kwargs):
        """
        get request.user 取得該user 的info
        """
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)


@router_url('member')
class MemberViewSet(MyMixin):
    serializer_class = MemberSerializer
    # 計算訂單total 跟下訂單次數
    queryset = serializers.Member.objects.annotate(
        pay_total=Coalesce(Sum('order__total_price'), 0, ),
        order_count=Coalesce(Count('order'), 0)
    )
    filter_backends = (filters.MemberFilter,)
    pagination_class = LimitOffsetPagination
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.MemberManagerEditPermission,
                          permissions.MemberManagerReadPermission]

    def get_serializer_class(self):
        """
        抓對應的serializer
        """
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
        # 要判斷角色 update 的時候 manager or member 才可以
        if self.action == 'update':
            authentication_classes = [MangerOrMemberAuthentication]
        return [auth() for auth in authentication_classes]

    def get_permissions(self):
        # update 判斷角色
        if self.action in ('create',):
            self.permission_classes = []
        if self.action in ('update',):
            self.permission_classes = [permissions.MemberAuthenticated]
        return [permission() for permission in self.permission_classes]

    @action(methods=['POST'], detail=False, authentication_classes=[], permission_classes=[])
    def register(self, request, *args, **kwargs):
        # 註冊其實就是create
        host = request.data.get('host')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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
        # 登入判斷
        data = request.data.copy()
        raw_password = data['password']
        del data['password']
        # 判斷帳號
        try:
            user = serializers.Member.objects.filter(status=True).get(**data)
        except Exception as e:
            return Response(data='帳號或密碼錯誤', status=403)
        # 判斷密碼
        if not user.check_password(raw_password):
            return Response(data='帳號或密碼錯誤', status=403)
        # 給token
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
        # 登出刪掉token
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
        註冊的驗證
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
        """
        忘記密碼 如果帳號對的話就寄信
        """
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
            subject='【 重設密碼 】HFMU - HaveFun Mens Underwear | 男性內褲會員重設密碼信',
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
        """
        取得寄信的連結後重新設定密碼
        """
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
        """
        更新自己的資料
        """
        kwargs['partial'] = True
        partial = kwargs.pop('partial', True)
        host = request.data.get('host')
        instance = self.get_object()
        account = request.data.get('account')
        if account and account != instance.account:
            instance.validate = False
            instance.set_validate_code()
            instance.save()
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
        """
        新增member address
        """
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
        """
        新增該user的member 喜愛的商品
        """
        user = request.user
        # 只有會員可以 無角色則是存在cookie
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
        # 取得該user 的order
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
        # memberwish create or delete
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
        # 抓最上層的 serializer 會自動抓下面的sub category
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
        """
        品牌 給前端看
        所以要做資料重新的format
        ex: 0-9 A-Z
        """
        from collections import defaultdict
        import string
        response = super().list(request, *args, **kwargs)
        data = response.data
        dct = defaultdict(list)
        ret = []
        for el in data:
            name = el['en_name']
            key = name[0].upper()
            if key in string.digits:
                key = '0-9'
            dct[key].append(el)
        i = 0
        for k in sorted(dct.keys()):
            children = []
            for el in sorted(dct[k], key=lambda d: d['en_name'].upper()):
                i += 1
                el['fake_id'] = i
                children.append(el)
            i += 1
            ret.append(dict(
                name=k,
                fake_id=i,
                children=children
            ))
        response.data = ret
        return response

    def destroy(self, request, *args, **kwargs):
        """
        要真的刪除 有issue 反應刪除後 不能再新增相同 name的 brand
        """
        Brand.original_objects.filter(pk=kwargs['pk']).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        """
        hfmu 不需要 其他專案則是有固定要抓product 的寫法
        """
        # new product 4
        queryset = self.filter_queryset(self.get_queryset())
        new_products = self.get_data(queryset[:28])
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
        """
        from index_page
        如果他要產生product data 就不用重複寫這麼多
        """
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
            # ret 要新增 最高價錢 跟最低 前端filter 會用到
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
        """
        購物車create 前先判斷是否db 有
        """
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
        # 計算購物車數量
        from django.contrib.auth.models import AnonymousUser
        count = 0
        if not isinstance(request.user, AnonymousUser):
            queryset = self.filter_queryset(self.get_queryset())
            for el in queryset:
                count += el.quantity
        return Response(dict(count=int(count)))

    @action(methods=['GET'], detail=False, authentication_classes=[MemberCheckAuthentication])
    def total(self, request, *args, **kwargs):
        # 計算購物車金額
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
                    spec1_en_name=product.data['level1_en_title'],
                    spec2_nen_ame=product.data['level2_en_title'],
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
        return queryset.filter(member=self.request.user)


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
        """
        如果不是manager 看到的免運費 只能看到 開啟的
        """
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
        # 因為這個是客製化的才要寫 他不適用id 做filter 而是discount code
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
        """
        如果member 只能要自己的
        """
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
        # 只抓第一筆
        serializer = self.get_serializer(queryset.first(), )
        return Response(serializer.data)


@router_url('membertoken')
class MemberTokenViewSet(MyMixin):
    queryset = serializers.MemberTokens.objects.all()
    serializer_class = serializers.MemberSerializer
    authentication_classes = [MemberCheckAuthentication]
    permission_classes = []

    def list(self, request, *args, **kwargs):
        # get member token
        ret = dict(token=isinstance(request.user, serializers.Member))
        ret['msg'] = request.META.get("HTTP_AUTHORIZATION")
        return Response(ret)


class PriceHandler:
    """
    抓價錢換算 美金跟台幣
    """
    def __init__(self):
        # todo 前幾天7月有問題
        # 如果看好了就可以改這個 url: https://rate.bot.com.tw/cr/
        self.url = 'https://rate.bot.com.tw/cr/2020-06'
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
        # 計算價錢匯率
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
    """
    抓cateogry 跟底下的ids
    給activity 抓出底下的products
    """
    queryset = Category.objects.all()
    ret = defaultdict(list)
    for el in queryset:
        if el.main_category:
            ret[el.main_category.id].append(el.id)
    delete_ids = []
    keys = ret.keys()
    for main_category_id in ret:
        target_list = ret[main_category_id]
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
        """
        ids: category
        將這些ids 裡面的product 全部加上activity_id
        我們榜的不是category 而是product
        """
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
                product.save()
        return Response(dict(msg='ok'), status=status.HTTP_201_CREATED)

    @action(methods=['POST'], detail=False)
    def del_category(self, request, *args, **kwargs):
        """
        ids: category
        將這些ids 裡面的product 全部加上activity_id
        我們榜的不是category 而是product
        """
        ids = request.data['ids']
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
                product.activity_id = None
                product.save()
        return Response(dict(msg='ok'), status=status.HTTP_201_CREATED)


@router_url('homeactivity')
class HomeActivityViewSet(MyMixin):
    queryset = serializers.HomeActivity.objects.all()
    serializer_class = serializers.HomeActivitySerializer
    authentication_classes = [TokenCheckAuthentication]
    permission_classes = [(permissions.ReadAuthenticated | permissions.CouponManagerEditPermission)]

    def list(self, request, *args, **kwargs):
        """
        首頁活動
        如果沒有的話就新增預設 為什麼在這邊新增，怕未來 run_init 也不要用了
        """
        if not HomeActivity.objects.first():
            HomeActivity.objects.create(
                ch_name='預設文字',
                en_name='預設文字',
            )
        return super().list(request, *args, **kwargs)


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
        """
        訂單資料輸出 給file name 讓前端可以找路徑下載
        """
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
        # 組成資料
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
        # 轉csv 並提供前端路徑 只有一個路徑沒有多寫
        # 一來不想要越來越多csv 二來 後端manager 不可能很多 不可能很多人同時輸出
        file_name = f'訂單資訊.csv'
        df.to_csv(f'./media/{file_name}', encoding='big5')
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
        # member 輸出
        ids = request.query_params.get('ids')
        ids = ids.split(',')
        queryset = self.filter_queryset(self.get_queryset()).filter()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        ret = []
        # 組成資料
        for mid in ids:
            el = self.get_serializer(queryset.filter(pk=mid), many=True).data
            dct = {
                '會員編號': el[0]['member_number'],
                '會員所在地': el[0]['local'],
                '姓名': el[0]['name'],
                '會員帳號': el[0]['account'],
                '會員生日': el[0]['birthday'],
                'LINE ID': el[0]['line_id'],
                '會員電話': el[0]['phone'],
                '會員手機': el[0]['cellphone'],
                '內部備註': el[0]['remarks'],
                '註冊時間': el[0]['join_at'],
                '回饋點數': el[0]['returns'],
                '消費次數': el[0]['order_count'],
                '消費金額': el[0]['pay_total'],
                '狀態': '啟用中' if el[0]['status'] else '停用中',
            }
            ret.append(dct)
        df = pd.DataFrame(data=ret)
        # 轉csv 並提供前端路徑 只有一個路徑沒有多寫
        # 一來不想要越來越多csv 二來 後端manager 不可能很多 不可能很多人同時輸出
        file_name = f'會員資訊.csv'
        df.to_csv(f'./media/{file_name}', encoding='big5')
        return Response(data=dict(
            file_name=file_name,
        ))


@router_url('exportmemberemail')
class ExportMemberEmailViewSet(ListModelMixin, viewsets.GenericViewSet):
    queryset = serializers.Member.objects.filter(email_status=True).all()
    serializer_class = serializers.MemberGetEmailSerializer
    authentication_classes = [MangerOrMemberAuthentication]
    permission_classes = [(
            permissions.MemberAuthenticated | permissions.MemberManagerEditPermission & permissions.MemberManagerReadPermission)]

    def list(self, request, *args, **kwargs):
        """
        輸出會員email csv
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        ret = []
        # 組成資料
        for el in serializer.data:
            dct = {
                '會員編號': el['member_number'],
                '姓名': el['name'],
                '會員帳號': el['account'],
            }
            ret.append(dct)
        df = pd.DataFrame(data=ret)
        # 轉csv 並提供前端路徑 只有一個路徑沒有多寫
        # 一來不想要越來越多csv 二來 後端manager 不可能很多 不可能很多人同時輸出
        file_name = f'訂閱電子報使用者mail資訊.csv'
        df.to_csv(f'./media/{file_name}', encoding='big5')
        return Response(data=dict(
            file_name=file_name,
        ))
