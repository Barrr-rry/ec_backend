from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import exceptions
from rest_framework import serializers
import json
import datetime
from rest_framework.validators import UniqueValidator
from django.http.request import QueryDict
# check admin
from .models import (BannerContent, Banner, File, Permission, Manager, AdminTokens, Member, Brand, Product,
                     Specification, MemberTokens, Order, MemberStore, Reward, RewardRecord, MemberAddress,
                     ProductImage, Category, Tag, TagImage, Cart, ProductQuitShot, FreeShipping, Coupon,
                     MemberWish, ConfigSetting, SpecificationDetail, Country, RewardRecordTemp, Activity
                     )
from django.utils.functional import cached_property
from rest_framework.utils.serializer_helpers import BindingDict
from django.utils import timezone
from .serialierlib import NestedModelSerializer, DefaultModelSerializer, HiddenField, hiddenfield_factory, CommonMeta, \
    PermissionCommonMeta, UserCommonMeta, CreateCommonMeta
import uuid
from django.contrib.auth.hashers import make_password
from django.core import validators
from api.sdk import shipping_map
from api.util import get_config

fmt = '%Y-%m-%d %H:%M:%S'


class MemberHiddenField:
    def set_context(self, serializer_field):
        if not isinstance(serializer_field.context['request'].user, Member):
            raise serializers.ValidationError('操作錯誤')
        self.target = serializer_field.context['request'].user

    def __call__(self, *args, **kwargs):
        return self.target


def serializer_factory(cls_name, cls, fds):
    class Meta(cls.Meta):
        fields = fds

    return type(cls_name, (cls,), dict(Meta=Meta))


def response_time(self, instance, key):
    if getattr(instance, key) is None:
        return None
    else:
        return getattr(instance, key).strftime(fmt)


class BannerSerializer(NestedModelSerializer):
    class Meta(CommonMeta):
        model = Banner
        nested_fields = {'content': 'banner'}  # {related_name: field_name}
        update_fields = {'content': ['title', 'subtitle', 'description', 'button']}


class FileSerializer(serializers.ModelSerializer):
    filename = serializers.SerializerMethodField('get_file')

    class Meta(CommonMeta):
        model = File

    def get_file(self, instance):
        return instance.file.name


class PermissionSerializer(DefaultModelSerializer):
    class Meta(CommonMeta):
        model = Permission

    def update(self, instance, validated_data):
        data = validated_data
        if instance.highest_permission:
            data = dict()
            for key in ['name', 'description']:
                if key not in validated_data:
                    continue
                data[key] = validated_data[key]
        return super().update(instance, data)


class ManagerSerializer(DefaultModelSerializer):
    password = serializers.CharField(
        max_length=128, help_text="密碼", write_only=True,
        validators=[
            validators.RegexValidator(regex=r'^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z0-9]{6,12}$',
                                      message='請輸入 6 - 12 個英數混合密碼')
        ]
    )
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    permission_description = serializers.CharField(source='permission.description', read_only=True)
    permission_role_manage = serializers.CharField(source='permission.role_manage', read_only=True)
    permission_member_manage = serializers.CharField(source='permission.member_manage', read_only=True)
    permission_order_manage = serializers.CharField(source='permission.order_manage', read_only=True)
    permission_banner_manage = serializers.CharField(source='permission.banner_manage', read_only=True)
    permission_catalog_manage = serializers.CharField(source='permission.catalog_manage', read_only=True)
    permission_product_manage = serializers.CharField(source='permission.product_manage', read_only=True)
    permission_coupon_manage = serializers.CharField(source='permission.coupon_manage', read_only=True)
    permission_highest_permission = serializers.BooleanField(source='permission.highest_permission', read_only=True)

    email = serializers.EmailField(validators=[
        UniqueValidator(
            queryset=Manager.original_objects.all(),
            message="Email已經被註冊",
        )]
    )

    class Meta:
        model = Manager
        exclude = [
            'created_at',
            'updated_at',
            'deleted_at',
            'deleted_status',
            'last_login',
        ]

    # def validate(self, data, request):
    #     """
    #     Check that start is before finish.
    #     """
    #     user = request.user
    #     if self.instance and self.instance.permission.highest_permission and user.permission.highest_permission is False:
    #         raise serializers.ValidationError("超級管理員不可更動")
    #     return data

    def create(self, validated_data):
        manager = Manager(**validated_data)
        manager.set_password(validated_data['password'])
        manager.save()
        return manager

    def update(self, instance, validated_data):
        if validated_data.get('password'):
            validated_data['password'] = make_password(validated_data.get('password'))
        return super().update(instance, validated_data)


class ManagerLoginSerializer(DefaultModelSerializer):
    class Meta:
        model = Manager
        fields = ('email', 'password')


class MemberLoginSerializer(DefaultModelSerializer):
    class Meta:
        model = Member
        fields = ('account', 'password')


class MemberAddressSerializer(DefaultModelSerializer):
    member = serializers.HiddenField(default=MemberHiddenField())

    class Meta(CommonMeta):
        model = MemberAddress


class RewardRecordSerializer(DefaultModelSerializer):
    end_date = serializers.DateField(read_only=True, format="%Y-%m-%d")
    created_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%d")

    class Meta(CreateCommonMeta):
        model = RewardRecord


class OrderForMemberSerializer(DefaultModelSerializer):
    created_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%d")
    rewrad = RewardRecordSerializer(many=True, read_only=True)

    class Meta(CreateCommonMeta):
        model = Order


class MemberSerializer(DefaultModelSerializer):
    password = serializers.CharField(
        max_length=128, help_text="密碼", write_only=True,
        validators=[
            validators.RegexValidator(regex=r'^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z0-9]{6,12}$',
                                      message='請輸入 6 - 12 個英數混合密碼')
        ]
    )
    cellphone = serializers.CharField(max_length=64, required=True, help_text="會員手機 手機", validators=[
        UniqueValidator(
            queryset=Member.original_objects.all(),
            message="電話號碼已經被註冊",
        )])
    member_number = serializers.CharField(max_length=64, required=False, help_text="會員編號 ezgo201912190000", validators=[
        UniqueValidator(
            queryset=Member.original_objects.all(),
            message="會員編號已經被註冊",
        )]
                                          )
    returns = serializers.SerializerMethodField()
    account = serializers.EmailField(validators=[
        UniqueValidator(
            queryset=Member.objects.all(),
            message="Email已經被註冊",
        )]
    )
    join_at = serializers.DateTimeField(source='created_at', read_only=True, format="%Y-%m-%d %H:%M:%S")
    memberaddress = MemberAddressSerializer(many=True, read_only=True)
    order = OrderForMemberSerializer(many=True, read_only=True)

    class Meta(UserCommonMeta):
        model = Member

    def get_returns(self, obj):
        return obj.get_rewards()

    def validate(self, data):
        """
        Check that start is before finish.
        """
        # todo 確認是否真的必填 因為已經有 MemberAddress 還需要這邊的電話幹嘛?

        # if data.get('cellphone') is None and data.get('phone') is None:
        #     raise serializers.ValidationError("電話與手機擇一必填")
        return data

    def create(self, validated_data):
        if self.context.get('view').action == 'create':
            validated_data['validate'] = True
        # 改成前端給
        resave = False
        if not validated_data.get('member_number'):
            now = timezone.now().strftime('%Y%m%d%H%M%S')
            validated_data['member_number'] = uuid.uuid1()
            resave = True
        member = Member(**validated_data)
        member.set_password(validated_data['password'])
        member.set_validate_code()
        member.save()
        if resave:
            member.member_number = f'M{now}{member.id}'
            member.save()
        return member

    def update(self, instance, validated_data):
        if validated_data.get('password'):
            validated_data['password'] = make_password(validated_data.get('password'))
        return super().update(instance, validated_data)


class MemberForgotPasswordToSrtSerializer(DefaultModelSerializer):
    new_password = serializers.CharField(
        max_length=128, help_text="新密碼", write_only=True,
        validators=[
            validators.RegexValidator(regex=r'^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z0-9]{6,12}$',
                                      message='請輸入 6 - 12 個英數混合密碼')
        ]
    )
    password_confirm = serializers.CharField(
        max_length=128, help_text="再次確認密碼", write_only=True,
        validators=[
            validators.RegexValidator(regex=r'^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z0-9]{6,12}$',
                                      message='請輸入 6 - 12 個英數混合密碼')
        ]
    )

    class Meta:
        model = Member
        fields = ('new_password', 'password_confirm')

    def update(self, instance, validated_data):
        instance.set_password(validated_data.get('new_password'))
        instance.save()
        return instance


class MemberPasswordSerializer(DefaultModelSerializer):
    password = serializers.CharField(
        max_length=128, help_text="密碼", write_only=True,
        # validators=[
        #     validators.RegexValidator(regex=r'^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z0-9]{6,12}$',
        #                               message='請輸入 6 - 12 個英數混合密碼')
        # ]
    )
    new_password = serializers.CharField(
        max_length=128, help_text="新密碼", write_only=True,
        validators=[
            validators.RegexValidator(regex=r'^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z0-9]{6,12}$',
                                      message='請輸入 6 - 12 個英數混合密碼')
        ]
    )
    password_confirm = serializers.CharField(
        max_length=128, help_text="再次確認密碼", write_only=True,
        validators=[
            validators.RegexValidator(regex=r'^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z0-9]{6,12}$',
                                      message='請輸入 6 - 12 個英數混合密碼')
        ]
    )

    class Meta:
        model = Member
        fields = ('new_password', 'password', 'password_confirm')

    def validate(self, data):
        """
        Check that start is before finish.
        """
        request = self.context.get('request')
        errors = dict()
        if not request.user.check_password(data.get('password')):
            errors['password'] = '請輸入正確密碼'

        if data.get('new_password') != data.get('password_confirm'):
            errors['password_confirm'] = '密碼不一致'
            raise serializers.ValidationError(errors)
        return data


class CategorySerializer(DefaultModelSerializer):
    sub_categories = serializers.SerializerMethodField(read_only=True, method_name="get_sub_categories")
    has_product = serializers.SerializerMethodField(read_only=True)

    class Meta(CommonMeta):
        model = Category

    def get_sub_categories(self, obj):
        """ self referral field """
        serializer = CategorySerializer(
            instance=obj.sub_categories.all(),
            many=True
        )
        return serializer.data

    def get_has_product(self, obj):
        """ self referral field """
        if obj.product.count():
            return True
        else:
            return False


class BrandSerializer(DefaultModelSerializer):
    has_product = serializers.SerializerMethodField(read_only=True)

    class Meta(CommonMeta):
        model = Brand

    def get_has_product(self, obj):
        """ self referral field """
        if obj.product.count():
            return True
        else:
            return False


class ProductImageSerializer(DefaultModelSerializer):
    specification_name = serializers.CharField(max_length=128, write_only=True, required=False, help_text='規格名字')

    class Meta:
        model = ProductImage
        fields = ('main_image', 'image_url', 'specification_name', 'specification')


# todo
class ProductListSerializer(DefaultModelSerializer):
    productimages = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'product_number', 'productimages')


class SpecificationSerializer(DefaultModelSerializer):
    class Meta(CommonMeta):
        model = Specification


class SpecificationWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=128, help_text='規格名稱')
    id = serializers.IntegerField(help_text='規格id', required=False)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class SpecificationDetailSerializer(DefaultModelSerializer):
    spec1_name = serializers.SerializerMethodField()
    spec2_name = serializers.SerializerMethodField()

    class Meta(CommonMeta):
        model = SpecificationDetail

    def get_spec1_name(self, instance):
        return instance.level1_spec.name

    def get_spec2_name(self, instance):
        level2_spec = instance.level2_spec
        return level2_spec.name if level2_spec else None


class ProductSerializer(DefaultModelSerializer):
    product_number = serializers.CharField(max_length=256, help_text="商品編號 P+mmdd+流水號", required=False)
    brand_en_name = serializers.CharField(source='brand.en_name', read_only=True)
    brand_cn_name = serializers.CharField(source='brand.cn_name', read_only=True)
    tag = serializers.PrimaryKeyRelatedField(many=True, required=False, help_text='標籤流水號', queryset=Tag.objects.all())
    tag_detail = serializers.SerializerMethodField(read_only=True)
    category = serializers.PrimaryKeyRelatedField(many=True, required=False, help_text='分類流水號',
                                                  queryset=Category.objects.all())
    tag_name = serializers.CharField(source='tag.name', read_only=True)
    categories = CategorySerializer(many=True, read_only=True, source='category')
    specification_level1 = SpecificationWriteSerializer(many=True, write_only=True,
                                                        help_text='規格name ex: [{name: \'規格\']')
    specification_level2 = SpecificationWriteSerializer(many=True, write_only=True,
                                                        required=False,
                                                        help_text='規格name ex: [{name: \'規格\']')
    specifications_detail_data = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False,
        help_text="規格etail ex: {'level1_spec': '213', 'weight': 222, 'price': 222, 'fake_price': 222, 'inventory_status': 1}]")

    productimages = ProductImageSerializer(many=True, help_text='Product Images')
    specifications_detail = SpecificationDetailSerializer(many=True, read_only=True)
    specifications = SpecificationSerializer(many=True, read_only=True)
    status_display = serializers.SerializerMethodField(read_only=True)
    inventory_status_display = serializers.SerializerMethodField(read_only=True)

    class Meta(CommonMeta):
        model = Product

    def get_tag_detail(self, instance):
        return TagListSerializer(many=True, instance=instance.tag.all()).data

    def get_inventory_status_display(self, instance):
        specificationdetails = SpecificationDetail.objects.filter(product=instance.id).all()
        for specificationdetail in specificationdetails:
            if (specificationdetail.inventory_status == 1) or (specificationdetail.quantity > 10):
                return '庫存充足'
            elif (specificationdetail.inventory_status == 2) or (specificationdetail.quantity <= 0):
                return '無庫存'
            elif 0 < specificationdetail.quantity <= 10:
                return '庫存不足'

    def get_status_display(self, instance):
        if instance.status:
            return '上架中'
        return '已下架'

    def create(self, validated_data):
        now = timezone.now().strftime('%m%d')
        validated_data['product_number'] = uuid.uuid1()
        product_images = self.pull_validate_data(validated_data, 'productimages', [])
        specification_level1 = self.pull_validate_data(validated_data, 'specification_level1', [])
        specification_level2 = self.pull_validate_data(validated_data, 'specification_level2', [])
        specifications_detail_data = self.pull_validate_data(validated_data, 'specifications_detail_data', [])
        category = self.pull_validate_data(validated_data, 'category', [])
        tag = self.pull_validate_data(validated_data, 'tag')

        with transaction.atomic():
            product = Product(**validated_data)
            product.save()
            product.product_number = f'P{now}{product.id}'
            for cat in category:
                product.category.add(cat)
            for t in tag:
                product.tag.add(t)
            product.save()

            for specification in specification_level1:
                specification['product'] = product
                specification['level'] = 1
                Specification.objects.create(**specification)

            for specification in specification_level2:
                specification['product'] = product
                specification['level'] = 2
                Specification.objects.create(**specification)

            for product_image in product_images:
                product_image['product'] = product
                if 'specification_name' in product_image:
                    specification_name = product_image['specification_name']
                    del product_image['specification_name']
                    specification = Specification.objects.filter(product=product, name=specification_name).first()
                    product_image['specification'] = specification
                ProductImage.objects.create(**product_image)

            for spec_detail in specifications_detail_data:
                for key in ['level1_spec', 'level2_spec']:
                    if key in spec_detail:
                        spec = Specification.objects.filter(product=product, name=spec_detail[key]).first()
                        spec_detail[key] = spec

                spec_detail['product'] = product
                SpecificationDetail.objects.create(**spec_detail)

        return product

    def update(self, instance, validated_data):
        def get_ids(items):
            ret = []
            for item in items:
                _id = item.get('id')
                if _id:
                    ret.append(_id)
            return ret

        now = timezone.now().strftime('%m%d')
        product_images = self.pull_validate_data(validated_data, 'productimages', [])
        specification_level1 = self.pull_validate_data(validated_data, 'specification_level1', [])
        specification_level2 = self.pull_validate_data(validated_data, 'specification_level2', [])
        specifications_detail_data = self.pull_validate_data(validated_data, 'specifications_detail_data', [])
        category = self.pull_validate_data(validated_data, 'category', [])
        tag = self.pull_validate_data(validated_data, 'tag')
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            # category and tag
            instance.category.clear()
            instance.tag.clear()
            for cat in category:
                instance.category.add(cat)
            for t in tag:
                instance.tag.add(t)
            instance.save()
            ids_level1 = get_ids(specification_level1)
            ids_level2 = get_ids(specification_level2)
            Specification.original_objects.filter(product=instance). \
                exclude(id__in=ids_level1).exclude(id__in=ids_level2).delete()
            for specification in specification_level1:
                # create or update
                if specification.get('id'):
                    target = Specification.objects.get(pk=specification.get('id'))
                    target.name = specification['name']
                    target.save()
                else:
                    specification['product'] = instance
                    specification['level'] = 1
                    Specification.objects.create(**specification)

            for specification in specification_level2:
                # create or update
                if specification.get('id'):
                    target = Specification.objects.get(pk=specification.get('id'))
                    target.name = specification['name']
                    target.save()
                else:
                    specification['product'] = instance
                    specification['level'] = 2
                    Specification.objects.create(**specification)

            ProductImage.original_objects.filter(product=instance).delete()
            for product_image in product_images:
                product_image['product'] = instance
                if 'specification_name' in product_image:
                    specification_name = product_image['specification_name']
                    del product_image['specification_name']
                    specification = Specification.objects.filter(product=instance, name=specification_name).first()
                    product_image['specification'] = specification
                ProductImage.objects.create(**product_image)

            detail_ids = get_ids(specifications_detail_data)
            SpecificationDetail.original_objects.filter(product=instance).exclude(id__in=detail_ids).delete()
            for spec_detail in specifications_detail_data:
                for key in ['level1_spec', 'level2_spec']:
                    if key in spec_detail:
                        spec = Specification.objects.filter(product=instance, name=spec_detail[key]).first()
                        spec_detail[key] = spec
                spec_detail['product'] = instance
                # create or update
                if spec_detail.get('id'):
                    target = SpecificationDetail.objects.get(pk=spec_detail.get('id'))
                    for key in spec_detail:
                        setattr(target, key, spec_detail[key])
                    target.save()
                else:
                    SpecificationDetail.objects.create(**spec_detail)

        return instance


class TagListSerializer(DefaultModelSerializer):
    tag_image_name = serializers.CharField(source='tag_image.name', read_only=True)
    tag_image_image_url = serializers.CharField(source='tag_image.image_url', read_only=True)

    class Meta(CommonMeta):
        model = Tag


class TagSerializer(DefaultModelSerializer):
    tag_image_image_url = serializers.CharField(source='tag_image.image_url', read_only=True)
    # todo
    product_ids = serializers.ListField(child=serializers.IntegerField(min_value=0), write_only=True)
    has_product = serializers.SerializerMethodField(read_only=True)
    products = ProductListSerializer(many=True, read_only=True, source='product')

    class Meta(CommonMeta):
        model = Tag

    # @staticmethod
    # def setup_eager_loading(queryset):
    #     """ Perform necessary eager loading of data. """
    #     queryset = queryset.prefetch_related('products')
    #     return queryset

    def validate_product_ids(self, value):
        count = Product.objects.filter(id__in=value, tag__isnull=False).count()
        if count:
            # todo 只有多標籤可以解決這個問題
            pass
            # raise serializers.ValidationError('product has tag')
        return value

    def get_has_product(self, obj):
        """ self referral field """
        if obj.product.count():
            return True
        else:
            return False

    def create(self, validated_data):
        product_ids = self.pull_validate_data(validated_data, 'product_ids')
        with transaction.atomic():
            instance = super(TagSerializer, self).create(validated_data)
            products = Product.objects.filter(id__in=product_ids)
            for product in products:
                if product.tag:
                    # todo 只有多標籤可以解決這個問題
                    pass
                    # raise serializers.ValidationError('product_ids has tag')
                product.tag.add(instance)
                product.save()
            return instance

    def update(self, instance, validated_data):
        product_ids = self.pull_validate_data(validated_data, 'product_ids')
        with transaction.atomic():
            instance = super(TagSerializer, self).update(instance, validated_data)
            instance.product.clear()
            products = Product.objects.filter(id__in=product_ids)
            for product in products:
                product.tag.add(instance)
                product.save()
            return instance


class TagImageSerializer(DefaultModelSerializer):
    class Meta(CommonMeta):
        model = TagImage


class CartSerializer(DefaultModelSerializer):
    member = serializers.HiddenField(default=MemberHiddenField())
    spec1_name = serializers.SerializerMethodField()
    spec2_name = serializers.SerializerMethodField()

    class Meta(CommonMeta):
        model = Cart

    def validate(self, data):
        """
        Check that start is before finish.
        """
        quantity = data['quantity']
        product = data['product']
        specification_detail = data['specification_detail']
        if not product.status:
            raise serializers.ValidationError("商品已下架")
        for specification in product.specifications_detail.all():
            if specification == specification_detail and specification.quantity and specification.quantity < quantity:
                raise serializers.ValidationError("大於商品數量")
            elif specification == specification_detail and specification.inventory_status and specification.inventory_status == 0:
                raise serializers.ValidationError("商品已無庫存")
        return data

    def get_spec1_name(self, instance):
        return instance.specification_detail.level1_spec.name

    def get_spec2_name(self, instance):
        level2_spec = instance.specification_detail.level2_spec
        return level2_spec.name if level2_spec else None

    def update(self, instance, validated_data):
        find_instance = Cart.objects.filter(member=instance.member, product=instance.product,
                                            specification_detail=validated_data['specification_detail']).first()
        if find_instance and instance.specification_detail != validated_data.get('specification_detail'):
            find_instance.quantity += instance.quantity
            find_instance.save()
            instance.delete()
            return find_instance
        else:
            return super().update(instance, validated_data)


class ProductForCartSerializer(ProductListSerializer):
    specifications_detail = SpecificationDetailSerializer(many=True, read_only=True)
    specifications = SpecificationSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'product_number', 'productimages', 'specifications',
                  'level1_title', 'level2_title',
                  'specifications_detail')


class MemberWishSerializer(DefaultModelSerializer):
    product_detail = ProductForCartSerializer(read_only=True, many=False, source='product')
    join_at = serializers.DateTimeField(source='created_at', read_only=True, format="%Y-%m-%d")
    member = serializers.HiddenField(default=MemberHiddenField())

    class Meta(CommonMeta):
        model = MemberWish


class CartResposneSerializer(CartSerializer):
    product = ProductForCartSerializer(read_only=True)
    specification_detail = SpecificationDetailSerializer(read_only=True)


class RewardSerializer(DefaultModelSerializer):
    class Meta(CommonMeta):
        model = Reward


class OrderSerializer(DefaultModelSerializer):
    member = serializers.HiddenField(default=MemberHiddenField())
    callback_url = serializers.CharField(max_length=256, write_only=True, help_text='回傳網址', required=False)
    member_name = serializers.CharField(source='member.name', read_only=True, help_text='會員名稱')
    member_account = serializers.CharField(source='member.account', read_only=True, help_text='會員帳號')
    member_cellphone = serializers.CharField(source='member.cellphone', read_only=True, help_text='會員電話')
    created_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%d")
    display_remark_date = serializers.DateTimeField(format="%Y-%m-%d", read_only=True, source='remark_date')
    coupon_discount_code = serializers.CharField(source='coupon.discount_code', read_only=True)
    shipping_status_display = serializers.SerializerMethodField()
    rewrad = RewardRecordSerializer(many=True, read_only=True)
    coupon_id = serializers.IntegerField(write_only=True, required=False, help_text='coupon id')

    class Meta:
        model = Order
        exclude = [
            'updated_at',
            'deleted_at',
            'deleted_status',
        ]

    def validate(self, data):
        product_shot = data['product_shot']
        product_shot = json.loads(product_shot)
        for product_detail in product_shot:
            quantity = product_detail['quantity']
            product_id = product_detail['id']
            product = Product.objects.filter(pk=product_id).first()
            specification_detail = product_detail['specification_detail']
            if not product.status:
                raise serializers.ValidationError("商品已下架")
            for specification in product.specifications_detail.all():
                if specification == specification_detail and specification.quantity and specification.quantity < quantity:
                    raise serializers.ValidationError("大於商品數量")
                elif specification == specification_detail and specification.inventory_status and specification.inventory_status == 0:
                    raise serializers.ValidationError("商品已無庫存")
        return data

    def get_shipping_status_display(self, instance):
        return shipping_map.shipping_mapping.get(str(instance.shipping_status))

    def create(self, validated_data):
        now = timezone.now().strftime('%Y%m%d%H%M%S')
        validated_data['order_number'] = uuid.uuid1()
        instance = Order.objects.create(**validated_data)
        instance.order_number = f'{now}{instance.id}'
        product_shot = json.loads(instance.product_shot)
        total_weight = 0
        config = get_config()
        for i in range(len(product_shot)):
            if config['weight']:
                total_weight += product_shot[i]['specification_detail']['weight'] * product_shot[i]['quantity']
            # 如果 config 有完整庫存功能 訂單來了要自己減少
            specification_detail = SpecificationDetail.objects.get(pk=product_shot[i]['specification_detail']['id'])
            if config['product_stock_setting'] == 3 and specification_detail.quantity is not None:
                specification_detail.quantity -= product_shot[i]['quantity']
                specification_detail.save()
        instance.total_weight = total_weight
        instance.save()
        return instance


class MemberStoreSerializer(DefaultModelSerializer):
    class Meta(CommonMeta):
        model = MemberStore


# todo 簡單做 先不管他 目前沒有用到
class ProductQuitShotSerializer(DefaultModelSerializer):
    class Meta(CommonMeta):
        model = ProductQuitShot

    def perform_create(self, validated_data):
        productquitshot = serializer.save()
        cart = Cart.objects.filter(member=isinstance.member)
        for i in range(cart):
            productquitshot.order_number = '12121212'
            productquitshot.product = cart.product
            productquitshot.quantity = cart.quantity
            productquitshot.title = cart.product.title
            productquitshot.weight = cart.product.weight
            productquitshot.price = cart.product.price
            productquitshot.specification = cart.product.specification
            cart.deleted_status = True
            productquitshot.save()
            cart.save()
        return productquitshot


class FreeShippingSerializer(DefaultModelSerializer):
    class Meta(CommonMeta):
        model = FreeShipping


class CouponSerializer(DefaultModelSerializer):
    type_text = serializers.SerializerMethodField()
    """
    正常
    過期
    超過個人使用限制
    超過全體使用限制
    
    過期：此張優惠券已過期
    找不到：查無此張優惠券
    超過全體使用次數限制：此張優惠券名額已滿
    超過個人使用次數限制：此張優惠券使用次數已達上限
    不符合優惠：您尚未達到此張優惠券門檻
    """
    status = serializers.SerializerMethodField()
    member = serializers.PrimaryKeyRelatedField(many=True, required=False, help_text='Member流水號',
                                                queryset=Member.objects.all())
    member_detail = serializers.SerializerMethodField(read_only=True)

    class Meta(CommonMeta):
        model = Coupon

    def get_member_detail(self, instance):
        return MemberSerializer(many=True, instance=instance.member.all()).data

    def get_status(self, instance):
        """
        1: 正常
        2: 過期
        3: 超過個人使用限制
        4: 超過全體使用限制
        """
        # todo 未完成
        now = timezone.now().date()
        ret = 1
        period_status = instance.start_time <= now < instance.end_time if instance.has_period else True
        if not period_status:
            ret = 2
            return ret

        in_member_use_limit = instance.order.filter(
            member=self.context['request'].user).count() < instance.member_use_limit \
            if instance.has_member_use_limit else True
        if not in_member_use_limit:
            ret = 3
            return ret
        in_coupont_use_limit = instance.order.count() < instance.coupon_use_limit \
            if instance.has_coupon_use_limit else True
        if not in_coupont_use_limit:
            ret = 4
            return ret
        return ret

    def get_type_text(self, instance):
        now = timezone.now().date()
        if not instance.has_period:
            return '啟用中'
        if instance.start_time <= now < instance.end_time:
            return '啟用中'
        else:
            return '已過期'


class ActivitySerializer(DefaultModelSerializer):
    product_ids = serializers.ListField(child=serializers.IntegerField(min_value=0), write_only=True)
    products = ProductListSerializer(many=True, read_only=True, source='product')

    class Meta(CommonMeta):
        model = Activity

    def create(self, validated_data):
        product_ids = self.pull_validate_data(validated_data, 'product_ids')
        with transaction.atomic():
            instance = super(ActivitySerializer, self).create(validated_data)
            products = Product.objects.filter(id__in=product_ids)
            for product in products:
                product.activity = instance
                product.save()
            return instance

    def update(self, instance, validated_data):
        product_ids = self.pull_validate_data(validated_data, 'product_ids')
        with transaction.atomic():
            instance = super(ActivitySerializer, self).update(instance, validated_data)
            queryset = Product.objects.filter(activity=instance)
            for pd in queryset:
                pd.activity = None
                pd.save()
            products = Product.objects.filter(id__in=product_ids)
            for product in products:
                product.activity = instance
                product.save()
            return instance


class ConfigSettingSerializer(DefaultModelSerializer):
    class Meta(CommonMeta):
        model = ConfigSetting
