from rest_framework.test import APITestCase
from .models import *
from . import serializers
from rest_framework.test import APIClient
from django.core.management import call_command
from pprint import pprint
import datetime
import json
from django.db.models import Q
import random
from fake_data import cn_name, en_name, get_random_letters, get_random_number, banner_args, categories, brands


class DefaultTestMixin:
    @classmethod
    def setUpTestData(cls):
        from run_init import main, test_email
        main(for_test=True)
        cls.anonymous_user = APIClient()
        cls.super_manager = cls.init_manager_apiclient(
            role_manage=2,
            member_manage=2,
            order_manage=2,
            banner_manage=2,
            catalog_manage=2,
            product_manage=2,
            coupon_manage=2,
            highest_permission=True,
        )
        member = Member.objects.get(account=test_email)
        token, created = MemberTokens.objects.get_or_create(user=member)
        cls.member_user = APIClient()
        cls.member_user.credentials(HTTP_AUTHORIZATION='Token ' + token.key)

    @classmethod
    def create_manager_to_get_token(cls, permission):
        user = Manager.objects.create(
            email=f'${get_random_letters(random.choice(range(10, 15)))}@conquers.co', password='1111',
            status=True, cn_name=random.choice(cn_name), en_name=random.choice(en_name),
            permission=permission)
        token, created = AdminTokens.objects.get_or_create(user=user)
        return token.key

    @classmethod
    def _init_manager_apiclient(cls, permission):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + cls.create_manager_to_get_token(permission))
        return client

    @classmethod
    def init_manager_apiclient(cls, **kwargs):
        params = dict(
            name='TEST',
            description='TEST',
            role_manage=0,
            member_manage=0,
            order_manage=0,
            banner_manage=0,
            catalog_manage=0,
            product_manage=0,
            coupon_manage=0,
            highest_permission=False,
        )
        params.update(**kwargs)
        permission = Permission.objects.create(
            **params
        )
        clinet = cls._init_manager_apiclient(permission=permission)
        return clinet

    @classmethod
    def create_member_to_get_token(cls):
        number_count = random.choice(range(5, 10))
        prefix_email = get_random_letters(random.choice(range(10, 15)))
        user = Member.objects.create(
            member_number=f"ezgo${get_random_number(number_count)}",
            name=random.choice(cn_name),
            phone=f'02-{get_random_number(8)}',
            cellphone=f'09{get_random_number(8)}',
            account=f'{prefix_email}@gmail.com',
            password='abc123',
            remarks='HI',
            status=False,
            validate=True,
        )
        user.set_password('abc123')
        token, created = MemberTokens.objects.get_or_create(user=user)
        return token.key

    @classmethod
    def init_member_apiclient(cls):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + cls.create_member_to_get_token())
        return client


class TestBanner(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'bigimage', 'smallimage', 'link', 'queue', 'status', 'display_type', 'start_time',
                     'end_time', 'content']
    contents = [
        dict(
            language_type=1,
            title='title_CH',
            subtitle='subtitle_CH',
            description='description_CH',
            button='button_CH',
        ),
        dict(
            language_type=2,
            title='title_EN',
            subtitle='subtitle_EN',
            description='description_EN',
            button='button_EN',
        )
    ]

    def test_banner_list(self):
        url = '/api/banner/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        item = r.data[0]
        self.assertEqual(set(item.keys()), set(self.response_keys))
        manager = self.init_manager_apiclient(name='123', banner_manage=0)
        r = manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 403)

    def test_banner_reed(self):
        instance = Banner.objects.first()
        url = f'/api/banner/{instance.id}/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # check response list
        self.assertEqual(list(r.data),
                         self.response_keys)

    def test_banner_post(self):
        url = '/api/banner/'
        data = dict(
            bigimage='default-banner-bigimage.png',
            smallimage='default-banner-smallimage.png',
            link='http://ezgo-buy.com/',
            queue=1,
            status=True,
            display_type=False,
            start_time='2019-06-20',
            end_time='2019-09-20',
            content=self.contents
        )
        r = self.super_manager.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)

        item = r.data
        self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_banner_update(self):
        instance = Banner.objects.first()
        url = f'/api/banner/{instance.id}/'
        data = dict(
            status=False
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        item = r.data
        self.assertEqual(set(item.keys()), set(self.response_keys))
        manager = self.init_manager_apiclient(name='123', banner_manage=1)
        r = manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 403)

    def test_banner_delete(self):
        instance = Banner.objects.first()
        url = f'/api/banner/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)
        manager = self.init_manager_apiclient(name='123', banner_manage=1)
        r = manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 403)

    def test_banner_list_noauth(self):
        # 判斷沒有auth可以lsit
        url = '/api/banner/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        item = r.data[0]
        self.assertEqual(list(item.keys()),
                         self.response_keys)


class TestPermission(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'name', 'description', 'role_manage', 'member_manage', 'order_manage', 'banner_manage',
                     'catalog_manage', 'product_manage', 'coupon_manage', 'highest_permission']

    def test_permission_list(self):
        url = '/api/permission/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        item = r.data[0]
        self.assertEqual(list(item.keys()),
                         self.response_keys)

    def test_noauth_permission(self):
        url = '/api/permission/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 401)

    def test_permission_post(self):
        url = '/api/permission/'
        i = random.randint(1, 10)
        data = dict(
            name='打打醬油',
            description='路過路過',
            role_manage=2,
            member_manage=2,
            order_manage=2,
            banner_manage=2,
            catalog_manage=2,
            product_manage=2,
            coupon_manage=2
        )
        r = self.super_manager.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)
        # request = reqponse
        for key in data:
            self.assertEqual(data[key], r.data[key])
        # response permission keys mapping
        self.assertEqual(sorted(list(r.data.keys())), sorted(self.response_keys))

    def test_permission_update(self):
        instance = Permission.objects.filter(highest_permission=False).last()
        url = f'/api/permission/{instance.id}/'
        data = dict(
            name='打打打醬油',
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        # return check
        for key in data:
            self.assertEqual(data[key], r.data[key])

    def test_permission_highest_permission_update(self):
        instance = Permission.objects.filter(highest_permission=True).last()
        url = f'/api/permission/{instance.id}/'
        data = dict(
            name='打打打醬油',
            description='test'
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        # return check
        for key in data:
            self.assertEqual(data[key], r.data[key])

    def test_permission_has_manager_delete_error(self):
        # 確認有manager不能刪除
        instance = Permission.objects.filter(highest_permission=False).last()
        url = f'/api/permission/{instance.id}/'
        # 確認 update 可以
        data = dict(
            name='打打打打醬油',
            description='路過路過',
            role_manage=2,
            member_manage=2,
            order_manage=2,
            banner_manage=2,
            catalog_manage=2,
            product_manage=2,
            coupon_manage=2
        )
        r = self.super_manager.put(url, data)
        self.assertEqual(r.status_code, 200)

        # 確認不能 delete
        r = self.super_manager.delete(url)
        self.assertEqual(r.status_code, 403)

    def test_permission_cantdelete(self):
        # 確認highest_permission=True不能刪除
        instance = Permission.objects.filter(highest_permission=True).first()
        url = f'/api/permission/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 403)

    def test_permission_delete(self):
        url = '/api/permission/'
        i = random.randint(1, 10)
        data = dict(
            name='打打醬油',
            description='路過路過',
            role_manage=2,
            member_manage=2,
            order_manage=2,
            banner_manage=2,
            catalog_manage=2,
            product_manage=2,
            coupon_manage=2
        )
        r = self.super_manager.post(url, data)
        instance = Permission.objects.filter(name='打打醬油').first()
        url = f'/api/permission/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)
        # 確認permisison
        manager = self.init_manager_apiclient(name='123', role_manage=1)
        r = manager.delete(url)
        self.assertEqual(r.status_code, 403)


class TestManager(DefaultTestMixin, APITestCase):
    # todo 報錯 AssertionError: The field 'validate' was included on serializer ManagerSerializer in the 'exclude' option, but does not match any model field.
    response_keys = ['id', 'permission_name', 'permission_description', 'permission_role_manage',
                     'permission_member_manage',
                     'permission_order_manage', 'permission_banner_manage', 'permission_catalog_manage',
                     'permission_product_manage',
                     'permission_coupon_manage', 'permission_highest_permission', 'email', 'cn_name', 'en_name',
                     'remarks',
                     'status', 'permission']

    def test_manager_list(self):
        url = '/api/manager/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        item = r.data[0]
        self.assertEqual(list(item.keys()),
                         self.response_keys)

    def test_manager_info(self):
        url = '/api/manager/info/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, dict)
        # request = reqponse
        item = r.data
        self.assertEqual(list(item.keys()),
                         self.response_keys)

    def test_manager_post(self):
        url = '/api/manager/'
        number = random.choices(range(9), k=9)
        number = ''.join(map(str, number))
        permission = Permission.objects.last()
        data = dict(
            email='ma11x@conquers.co',
            password=f'a{number}',
            status=True,
            cn_name='肉球',
            en_name='Meatball',
            permission=permission.id
        )
        r = self.super_manager.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)

    def test_manager_post_password_validate_error(self):
        # 確認密碼安全性
        url = '/api/manager/'
        number = random.choices(range(9), k=9)
        number = ''.join(map(str, number))
        permission = Permission.objects.last()
        data = dict(
            email='ma22x@conquers.co',
            password=f'{number}',
            status=True,
            cn_name='肉球',
            en_name='Meatball',
            permission=permission
        )
        r = self.super_manager.post(url, data)
        # status 400
        self.assertEqual(r.status_code, 400)

    def test_manager_update(self):
        instance = Manager.objects.filter(permission__highest_permission=False).first()
        url = f'/api/manager/{instance.id}/'
        data = dict(
            status=False,
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        # return check

    def test_manager_delete(self):
        instance = Manager.objects.filter(permission=2).first()
        url = f'/api/manager/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)
        manager = self.init_manager_apiclient(name='123', role_manage=1)
        r = manager.delete(url)
        self.assertEqual(r.status_code, 403)

    def test_manager_highest_permission(self):
        # if highest_permission = True cant update, delete
        instance = Manager.objects.filter(permission__highest_permission=True).first()
        url = f'/api/manager/{instance.id}/'
        r = self.super_manager.delete(url)
        # status 400
        # todo
        self.assertEqual(r.status_code, 204)
        manager = self.init_manager_apiclient(name='123', role_manage=1)
        r = manager.delete(url)
        self.assertEqual(r.status_code, 403)

    def test_manager_update_password_check(self):
        # 確認更改密碼
        instance = Manager.objects.filter(permission__highest_permission=False).last()
        new_psw = 'a123456'
        url = f'/api/manager/{instance.id}/'
        data = dict(password=new_psw)
        r = self.super_manager.put(url, data)
        # check response no password
        self.assertIsNone(r.data.get('password'))
        instance = Manager.objects.get(pk=instance.id)
        self.assertNotEqual(new_psw, instance.password)

    def test_noauth_manager(self):
        # 測試沒有權限可以list
        url = '/api/manager/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 401)


class TestMember(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'cellphone', 'member_number', 'returns', 'account', 'join_at', 'memberaddress', 'order',
                     'name',
                     'line_id',
                     'phone', 'remarks', 'status', 'expire_datetime',
                     'default_memberaddress']

    info_keys = ['id', 'cellphone', 'member_number', 'returns', 'account', 'join_at', 'memberaddress',
                 'order', 'validate', 'validate_code',
                 'name', 'line_id', 'phone', 'remarks', 'status', 'expire_datetime', 'default_memberaddress']

    order_keys = ['id', 'member_name', 'member_account', 'member_cellphone', 'created_at', 'display_remark_date',
                  'shipping_status_display',
                  'rewrad', 'shipping_name', 'total_price', 'freeshipping_price', 'product_price', 'coupon_price',
                  'reward_price', 'payment_type',
                  'order_number', 'phone', 'product_shot', 'bussiness_number', 'company_title', 'address',
                  'shipping_address',
                  'shipping_area', 'pay_status', 'pay_type', 'shipping_status', 'simple_status_display', 'to_store',
                  'store_type',
                  'store_id', 'cancel_order', 'order_remark', 'remark', 'remark_date', 'ecpay_data', 'coupon']

    memberwish_keys = ['id', 'product_detail', 'join_at', 'product']

    def test_member_list(self):
        url = '/api/member/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        item = r.data[0]
        self.assertEqual(sorted(list(item.keys())),
                         sorted(self.info_keys))

    def test_member_reed(self):
        instnace = Member.objects.first()
        url = f'/api/member/{instnace.id}/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # check response list
        self.assertEqual(sorted(list(r.data)),
                         sorted(self.info_keys))

    def test_member_post(self):
        url = '/api/member/'
        number = random.choices(range(9), k=9)
        number = ''.join(map(str, number))
        data = dict(
            name="康大闓",
            account=f"test{number}@conquers.co",
            phone=f"{number}",
            cellphone=f"{number}",
            remarks='test',
            password='1111wqwqw',
            status=True,
        )
        r = self.super_manager.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)
        self.assertTrue(Member.objects.get(pk=r.data['id']).validate)

    def register_respoonse(self):
        url = '/api/member/register/'
        number = random.choices(range(9), k=9)
        Member.objects.filter(account='max@conquers.co').delete()
        number = ''.join(map(str, number))
        data = dict(
            name="康大闓",
            account=f'max{number}@conquers.co',
            phone=f"{number}",
            cellphone=f"{number}",
            remarks='test',
            password='1111wqwqw',
            status=True,
        )
        r = self.anonymous_user.post(url, data)
        return r

    def test_member_register(self):
        r = self.register_respoonse()
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)
        self.assertFalse(Member.objects.get(pk=r.data['id']).validate)

    def test_member_register_validate_success(self):
        url = '/api/member/register_validate/'
        # test in expired
        r = self.register_respoonse()
        instance = Member.objects.get(pk=r.data['id'])
        data = dict(validate_code=instance.validate_code)
        r = self.anonymous_user.post(url, data)
        self.assertEqual(r.status_code, 200)

    def test_member_register_validate_fail(self):
        url = '/api/member/register_validate/'
        # test over expired
        r = self.register_respoonse()
        instance = Member.objects.get(pk=r.data['id'])
        instance.expire_datetime -= datetime.timedelta(days=20)
        instance.save()
        data = dict(validate_code=instance.validate_code)
        r = self.anonymous_user.post(url, data)
        self.assertEqual(r.status_code, 200)
        # 已經過期
        self.assertEqual(r.data['code'], 3)

    def test_member_memberaddress(self):
        url = '/api/member/memberaddress/'
        number = random.choices(range(9), k=9)
        number = ''.join(map(str, number))
        member = Member.objects.last()
        data = dict(
            member=member.id,
            shipping_name=member.name,
            phone=member.phone,
            shipping_address='高雄市',
            shipping_area='807',
        )
        r = self.member_user.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)

    def test_member_update(self):
        instance = Member.objects.first()
        url = f'/api/member/{instance.id}/'
        data = dict(
            name="品管人員",
            phone='121212'
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        # return check
        for key in data:
            self.assertEqual(data[key], r.data[key])

    def test_member_update_member(self):
        instance = Member.objects.filter(account='max@conquers.co').first()
        url = f'/api/member/{instance.id}/'
        data = dict(
            name="品管人員",
            phone='121212'
        )
        r = self.member_user.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        # return check
        for key in data:
            self.assertEqual(data[key], r.data[key])

    def test_member_login(self):
        url = '/api/member/login/'
        data = dict(
            account='max@conquers.co',
            password='1111'
        )
        r = self.super_manager.post(url, data, format='json')
        # status 201
        self.assertEqual(r.status_code, 200)

    def test_member_selfupdate(self):
        instance = Member.objects.first()
        url = f'/api/member/self_update/'
        data = dict(
            name="品管人員",
            phone='121212'
        )
        r = self.member_user.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        # return check
        for key in data:
            self.assertEqual(data[key], r.data[key])

    def test_member_delete(self):
        instance = Member.objects.first()
        url = f'/api/member/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)
        manager = self.init_manager_apiclient(name='123', member_manage=1)
        r = manager.delete(url)  # stauts 200
        self.assertEqual(r.status_code, 403)

    def test_member_info(self):
        url = '/api/member/info/'
        r = self.member_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, dict)
        # request = reqponse
        item = r.data
        info_keys = self.info_keys.copy()
        info_keys.append('rewards')
        self.assertEqual(sorted(list(item.keys())),
                         sorted(info_keys))

    def test_member_memberwish(self):
        pass
        # todo

    def test_member_order(self):
        url = '/api/member/order/'
        r = self.member_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse

    def test_noauth_member(self):
        url = '/api/member/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 401)


class TestCategory(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'sub_categories', 'has_product', 'name', 'image_url', 'main_category']

    def test_category_list(self):
        url = '/api/category/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        # todo
        # item = r.data[0]
        # self.assertEqual(list(item.keys()),
        #                  self.response_keys)

    def test_category_list_noauth(self):
        url = '/api/category/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        # todo
        # item = r.data[0]
        # self.assertEqual(list(item.keys()),
        #                  self.response_keys)

    def test_category_reed(self):
        instance = Category.objects.first()
        url = f'/api/category/{instance.id}/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # check response list
        # todo
        # self.assertEqual(list(r.data),
        #                  self.response_keys)

    def test_category_post(self):
        url = '/api/category/'
        data = dict(
            name='分類',
            image_url='c-01.svg',
            main_category=1
        )
        r = self.super_manager.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)

    def test_category_update(self):
        instance = Category.objects.first()
        url = f'/api/category/{instance.id}/'
        data = dict(
            name="品管人員",
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        # return check
        for key in data:
            self.assertEqual(data[key], r.data[key])

    def test_category_delete(self):
        instance = Category.objects.filter(sub_categories=None).first()
        url = f'/api/category/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)
        manager = self.init_manager_apiclient(name='123', catalog_manage=1)
        r = manager.delete(url)  # stauts 200
        self.assertEqual(r.status_code, 403)

    def test_catefory_list_noauth(self):
        url = '/api/category/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # todo
        # # request = reqponse
        # item = r.data[0]
        # self.assertEqual(list(item.keys()),
        #                  self.response_keys)


class TestTag(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'tag_image_image_url', 'products', 'has_product', 'name', 'tag_image']

    def test_tag_list(self):
        import time
        url = '/api/tag/'
        tStart = time.time()
        for i in range(10):
            r = self.super_manager.get(url)
        tEnd = time.time()
        print((tEnd - tStart) / 10)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        # todo
        # item = r.data[0]
        # self.assertEqual(list(item.keys()),
        #                  self.response_keys)

    def test_tag_reed(self):
        instance = Tag.objects.first()
        url = f'/api/tag/{instance.id}/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # check response list
        # todo
        # self.assertEqual(list(r.data),
        #                  self.response_keys)

    def test_tag_post(self):
        # create product_ids
        url = '/api/tag/'
        product_ids = list(set(map(lambda o: o.id, random.choices((Product.objects.filter(tag__isnull=True)), k=10))))
        tag_image = random.choice(TagImage.objects.all())
        data = dict(
            name='分類',
            product_ids=product_ids,
            tag_image=tag_image.id
        )
        r = self.super_manager.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)
        # check 數量一致
        tag_id = r.data['id']
        self.assertEqual(len(product_ids), Product.objects.filter(tag=tag_id, id__in=product_ids).count())

        # check validate
        product_ids.append(Product.objects.filter(tag__isnull=False).first().id)
        data['product_ids'] = product_ids
        r = self.super_manager.post(url, data)
        self.assertEqual(r.status_code, 201)

    def test_tag_update(self):
        instance = Tag.objects.first()
        url = f'/api/tag/{instance.id}/'
        product_ids = list(set(map(lambda o: o.id, random.choices((Product.objects.filter(tag__isnull=True)), k=10))))
        data = dict(
            name="品管人員",
            product_ids=product_ids
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        tag_id = r.data['id']
        self.assertEqual(len(product_ids), Product.objects.filter(tag=tag_id, id__in=product_ids).count())

        # return check
        for key in data:
            if key == 'product_ids':
                continue
            self.assertEqual(data[key], r.data[key])

    def test_tag_list_noauth(self):
        url = '/api/tag/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        # todo
        # item = r.data[0]
        # self.assertEqual(list(item.keys()),
        #                  self.response_keys)

    def test_tag_delete(self):
        instance = Tag.objects.filter(product__in=Product.objects.filter(deleted_status=False)).last()
        url = f'/api/tag/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 403)
        manager = self.init_manager_apiclient(name='123', catalog_manage=1)
        r = manager.delete(url)


class TestBrand(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'en_name', 'cn_name', 'index', 'menu', 'image_url', 'fake_id', 'has_product']

    def test_brand_list(self):
        url = '/api/brand/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        item = r.data[0]
        self.assertIsInstance(item['children'], list)
        item = item['children'][0]
        self.assertEqual(sorted(list(item.keys())), sorted(self.response_keys))

    def test_brand_reed(self):
        instance = Brand.objects.first()
        url = f'/api/brand/{instance.id}/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # check response list
        self.assertEqual(sorted(list(r.data)),
                         sorted(self.response_keys))

    def test_brand_post(self):
        tagimage = TagImage.objects.first()
        url = '/api/brand/'
        data = dict(
            cn_name='tagimage',
            en_name='分類',
            index=True,
            image_url='213'
        )
        r = self.super_manager.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)

    def test_brand_update(self):
        instance = Brand.objects.first()
        url = f'/api/brand/{instance.id}/'
        data = dict(
            cn_name="品管人員",
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        # return check
        for key in data:
            self.assertEqual(data[key], r.data[key])

    def test_brand_delete(self):
        url = '/api/brand/'
        data = dict(
            cn_name='tagimage',
            en_name='分類',
            index=True,
            image_url='213'
        )
        r = self.super_manager.post(url, data)
        instance = Brand.objects.first()
        url = f'/api/brand/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)
        manager = self.init_manager_apiclient(name='123', catalog_manage=1)
        r = manager.delete(url)  # stauts 200
        self.assertEqual(r.status_code, 403)

    def test_brand_list_noauth(self):
        url = '/api/brand/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        item = r.data[0]
        self.assertIsInstance(item['children'], list)
        item = item['children'][0]
        self.assertEqual(sorted(list(item.keys())), sorted(self.response_keys))


class TestProduct(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'product_number', 'brand_en_name', 'brand_cn_name', 'tag_name', 'name',
                     'order_count', 'categories',
                     'title', 'sub_title', 'weight', 'price', 'fake_price', 'inventory_status',
                     'description',
                     'description_2', 'detail_info', 'product_info',
                     'brand', 'tag', 'tag_detail', 'category', 'productimages', 'specifications']

    def test_product_list(self):
        url = '/api/product/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)

    def test_product_index_page(self):
        url = '/api/product/index_page/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, dict)

    def base_test_list(self, r, items):
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(items, list)
        item = items[0]
        self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_product_list_params(self):
        url = '/api/product/'
        r = self.super_manager.get(url, dict(limit=10, order_by='order_count'))
        items = r.data['results']
        self.base_test_list(r, items)
        r = self.super_manager.get(url, dict(limit=10, only_tag=True))
        items = r.data['results']
        self.base_test_list(r, items)

    def test_product_post(self):
        url = '/api/product/'
        data = dict(
            product_number=222,
            brand=1,
            name=222,
            title=222,
            sub_title=222,
            weight=222,
            price=222,
            fake_price=222,
            inventory_status=222,
            description=222,
            description_2=222,
            tag=1,
            category=[1, 2],
            specification=[
                {
                    "name": "213"
                }
            ],
            productimage=[
                {
                    "main_image": True,
                    "image_url": "23132222"
                }
            ]
        )
        r = self.super_manager.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)

    def test_product_update(self):
        instance = Product.objects.last()
        url = f'/api/product/{instance.id}/'
        data = dict(
            product_number=2222,
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)

    def test_product_delete(self):
        instance = Product.objects.first()
        url = f'/api/product/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)
        manager = self.init_manager_apiclient(name='123', product_manage=1)
        r = manager.delete(url)  # stauts 200
        self.assertEqual(r.status_code, 403)

    def test_product_list_noauth(self):
        url = '/api/product/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)

    def test_product_filter_price(self):
        url = f'/api/product/?max_price=600&min_price=300'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        for i in range(len(r.data)):
            if 300 > r.data[i]['price'] or 600 < r.data[i]['price']:
                self.fail()

    def test_product_list_pagination(self):
        url = f'/api/product/?offset=0&limit=1?keywords=存'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, dict)
        self.assertTrue('min_price' in r.data)
        self.assertTrue('max_price' in r.data)


class TestCart(DefaultTestMixin, APITestCase):
    response_keys = []

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        product = Product.objects.first()
        data = dict(
            product=product,
            specification=product.specifications.first(),
            quantity=1
        )
        member = Member.objects.filter(account='max@conquers.co').first()
        instance = Cart.objects.create(**data, member=member)

    def test_cart_list(self):
        url = '/api/cart/'
        r = self.member_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        item = r.data
        # todo 別的user 可否可以看到該cart
        # todo
        # self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_cart_post(self):
        url = '/api/cart/'
        product = Product.objects.first()
        data = dict(
            product=product.id,
            specification=product.specifications.first().id,
            quantity=1
        )
        r = self.member_user.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, dict)

        item = r.data
        # todo
        # self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_cart_update(self):
        instance = Cart.objects.last()
        product = Product.objects.first()
        url = f'/api/cart/{instance.id}/'
        data = dict(
            quantity=2,
            specification=product.specifications.first().id,
        )
        r = self.member_user.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        item = r.data
        # todo
        # self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_cart_delete(self):
        instance = Cart.objects.first()
        url = f'/api/cart/{instance.id}/'
        r = self.member_user.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)

    def test_cart_count(self):
        # todo
        pass

    def test_cart_total(self):
        # todo
        pass


class TestReward(DefaultTestMixin, APITestCase):
    response_keys = {'id', 'still_day', 'discount', 'status'}

    def test_reward_list(self):
        url = '/api/reward/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, dict)
        self.assertEqual(set(r.data.keys()), set(self.response_keys))

    def test_reward_post(self):
        url = '/api/reward/'
        data = dict(
            status=1,
            discount=20,
            still_day=30,
        )
        r = self.super_manager.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)

        item = r.data
        self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_reward_noauth(self):
        url = '/api/reward/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)


class TestRewardRecord(DefaultTestMixin, APITestCase):
    response_keys = {'id', 'end_date', 'start_date', 'point', 'use', 'member', 'order'}

    def test_rewardrecord_list(self):
        url = '/api/rewardrecord/'
        r = self.member_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        item = r.data[0]
        self.assertEqual(set(item.keys()), set(self.response_keys))
        # status 200

    def test_rewardrecord_update(self):
        instance = RewardRecord.objects.first()
        url = f'/api/rewardrecord/{instance.id}/'
        data = dict(
            point=1
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        item = r.data
        self.assertEqual(set(item.keys()), set(self.response_keys))
        # todo authentication_classes, permission_classes還沒設定好


class TestToken(DefaultTestMixin, APITestCase):
    response_keys = []

    def test_token_list(self):
        url = '/api/membertoken/'
        r = self.member_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, dict)
        self.assertTrue(r.data['token'])


class TestCoupon(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'type_text', 'status', 'role', 'method', 'discount', 'title', 'discount_code', 'image_url',
                     'start_time', 'end_time']

    def test_coupon_list(self):
        url = '/api/coupon/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        item = r.data[0]
        self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_coupon_reed(self):
        instance = Coupon.objects.first()
        url = f'/api/coupon/{instance.discount_code}/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # check response list
        self.assertEqual(list(r.data),
                         self.response_keys)

    def test_coupon_post(self):
        number = random.choices(range(9), k=9)
        number = ''.join(map(str, number))
        url = '/api/coupon/'
        data = dict(
            role=random.randint(0, 100),
            method=random.choice([1, 2]),
            discount=random.randint(0, 100),
            title='折價券',
            discount_code=f'DC{number}',
            image_url='11697.jpg',
            start_time='2019-06-20',
            end_time='2019-06-20',
        )
        r = self.super_manager.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)

        item = r.data
        self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_coupon_update(self):
        instance = Coupon.objects.first()
        url = f'/api/coupon/{instance.id}/'
        data = dict(
            title='折價券2',
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        item = r.data
        self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_coupon_delete(self):
        instance = Coupon.objects.first()
        url = f'/api/coupon/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)
        manager = self.init_manager_apiclient(name='123', coupon_manage=1)
        r = manager.delete(url)  # stauts 200
        self.assertEqual(r.status_code, 403)

    def test_coupon_list_noauth(self):
        url = '/api/coupon/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        # request = reqponse
        item = r.data[0]
        self.assertEqual(list(item.keys()),
                         self.response_keys)


class TestFreeShipping(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'logistics_type_text', 'logistics_type', 'title', 'role', 'weight', 'price']

    def test_freeshipping_list(self):
        url = '/api/freeshipping/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        item = r.data[0]
        self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_freeshipping_update(self):
        instance = FreeShipping.objects.first()
        url = f'/api/freeshipping/{instance.id}/'
        data = dict(
            title='折價券2',
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        item = r.data
        self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_noauth_freeshipping(self):
        url = '/api/freeshipping/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)


class TestMemberAddress(DefaultTestMixin, APITestCase):

    def test_memberaddress_update(self):
        instance = MemberAddress.objects.first()
        url = f'/api/memberaddress/{instance.id}/'
        data = dict(
            shippong_address='台北',
        )
        r = self.member_user.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)

    def test_memberaddress_delete(self):
        instance = MemberAddress.objects.first()
        url = f'/api/memberaddress/{instance.id}/'
        r = self.member_user.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)

    def test_noauth_memberaddress(self):
        instance = MemberAddress.objects.first()
        url = f'/api/memberaddress/{instance.id}/'
        r = self.anonymous_user.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 401)


class TestMemberWish(DefaultTestMixin, APITestCase):

    def test_memberwish_post(self):
        product = Product.objects.first()
        url = '/api/memberwish/'
        data = dict(
            product=product.id,
        )
        r = self.member_user.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, dict)

    def test_memberwish_delete(self):
        instance = MemberWish.objects.first()
        url = f'/api/memberwish/{instance.id}/'
        r = self.member_user.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)

    def test_noauth_memberwish(self):
        url = '/api/memberwish/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 401)


class TestOrder(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'member_name', 'member_account', 'member_cellphone', 'created_at', 'display_remark_date',
                     'shipping_status_display', 'rewrad', 'shipping_name', 'total_price', 'freeshipping_price',
                     'product_price',
                     'coupon_price', 'reward_price', 'payment_type', 'order_number', 'phone', 'product_shot',
                     'bussiness_number',
                     'company_title', 'address', 'shipping_address', 'shipping_area', 'pay_status', 'pay_type',
                     'shipping_status',
                     'simple_status_display', 'to_store', 'store_type', 'cancel_order', 'order_remark', 'remark',
                     'remark_date',
                     'ecpay_data', 'store_id', 'store_name', 'coupon']

    def _test_order_list(self, client):
        url = '/api/order/'
        r = client.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)
        item = r.data[0]
        # todo not done 401 問題解決 但是還有403 permission 要解決
        # todo
        # self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_order_list(self):
        self._test_order_list(self.super_manager)
        self._test_order_list(self.member_user)

    def test_order_noauth(self):
        url = '/api/order/'
        r = self.anonymous_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 401)

    def test_order_reed(self):
        instance = Order.objects.first()
        url = f'/api/order/{instance.id}/'
        r = self.super_manager.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # check response list
        # todo
        # self.assertEqual(list(r.data),
        #                  self.response_keys)

    def test_order_post(self):
        pass
        # todo

    def test_order_update(self):
        instance = Order.objects.first()
        url = f'/api/order/{instance.id}/'
        data = dict(
            address="台北市中正區",
        )
        r = self.super_manager.put(url, data)
        # status 200
        self.assertEqual(r.status_code, 200)
        # type dict
        self.assertIsInstance(r.data, dict)
        # return check
        for key in data:
            self.assertEqual(data[key], r.data[key])

    def test_order_delete(self):
        instance = Order.objects.first()
        url = f'/api/order/{instance.id}/'
        r = self.super_manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)
        manager = self.init_manager_apiclient(name='123', order_manage=1)
        r = manager.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 403)


class TestMemberStore(DefaultTestMixin, APITestCase):
    response_keys = ['id', 'sub_type', 'store_id', 'store_name', 'address', 'phone', 'member']

    def test_memberstore_list(self):
        url = '/api/memberstore/'
        data = dict(
            sub_type='HILIFE',
            store_id='2',
            store_name='2',
            address='2',
            phone='121',
            member=1
        )
        r = self.member_user.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        url = '/api/memberstore/'
        r = self.member_user.get(url)
        # status 200
        self.assertEqual(r.status_code, 200)
        # response type
        self.assertIsInstance(r.data, list)

    def test_memberstore_post(self):
        url = '/api/memberstore/'
        data = dict(
            sub_type='HILIFE',
            store_id='2',
            store_name='2',
            address='2',
            phone='121',
            member=1
        )
        r = self.member_user.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        # response type
        self.assertIsInstance(r.data, dict)

        item = r.data
        self.assertEqual(set(item.keys()), set(self.response_keys))

    def test_memberstore_delete(self):
        url = '/api/memberstore/'
        data = dict(
            sub_type='HILIFE',
            store_id='2',
            store_name='2',
            address='2',
            phone='121',
            member=1
        )
        r = self.member_user.post(url, data)
        # status 201
        self.assertEqual(r.status_code, 201)
        instance = MemberStore.objects.first()
        url = f'/api/memberstore/{instance.id}/'
        r = self.member_user.delete(url)
        # stauts 200
        self.assertEqual(r.status_code, 204)
