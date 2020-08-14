import datetime

from django.contrib.auth.models import AbstractBaseUser, UserManager, AbstractUser, PermissionsMixin
from django.db import models
from rest_framework.authtoken.models import Token as DefaultToken
from rest_framework import exceptions
from django.utils import timezone
from api.sdk import shipping_map
import uuid


class AdminTokens(DefaultToken):
    user = models.ForeignKey('Manager', related_name='auth_token', on_delete=models.CASCADE, )

    def expired(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        return now > self.created + datetime.timedelta(days=7)


class MemberTokens(DefaultToken):
    user = models.ForeignKey('Member', related_name='auth_token', on_delete=models.CASCADE, )

    def expired(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        return now > self.created + datetime.timedelta(days=7)


class ParanoidQuerySet(models.QuerySet):
    """
    Prevents objects from being hard-deleted. Instead, sets the
    ``date_deleted``, effectively soft-deleting the object.
    """

    def delete(self):
        for obj in self:
            obj.deleted_status = True
            obj.deleted_at = timezone.now()
            obj.save()


class ParanoidManager(models.Manager):
    """
    Only exposes objects that have NOT been soft-deleted.
    """

    def get_queryset(self):
        return ParanoidQuerySet(self.model, using=self._db).filter(
            deleted_status=False)


class DefaultAbstract(models.Model):
    deleted_status = models.BooleanField(default=False, help_text='資料刪除狀態')
    created_at = models.DateTimeField(auto_now_add=True, help_text='建立時間')
    updated_at = models.DateTimeField(null=True, help_text='更新時間')
    deleted_at = models.DateTimeField(null=True, blank=True, help_text='刪除時間')
    objects = ParanoidManager()
    original_objects = models.Manager()

    class Meta:
        abstract = True
        # todo check 是否要updated_at
        # ordering = ['-updated_at', '-created_at']
        ordering = ['-created_at']

    def delete(self, **kwargs):
        self.deleted_status = True
        self.deleted_at = timezone.now()
        self.save()


class File(DefaultAbstract):
    file = models.FileField()


class QueueMixin:
    class Meta:
        ordering = ['queue', '-updated_at', '-created_at']

    def save(self, validate=True, *args, **kwargs):
        if validate:
            meta = self._meta
            Model = meta.concrete_model
            filter_params = dict(
                deleted_status=False,
            )
            ret = super().save(*args, **kwargs)
            objs = Model.objects.filter(**filter_params).order_by('queue', 'updated_at', '-created_at')
            check_filter = True

            for index, obj in enumerate(objs):
                if self.id == obj.id and self.queue != index + 1:
                    check_filter = False
                if self.id == obj.id:
                    break
            if not check_filter:
                objs = Model.objects.filter(**filter_params).order_by('queue', '-updated_at', '-created_at')
            for index, obj in enumerate(objs):
                obj.queue = index + 1
                obj.save(validate=False)
        else:
            ret = super().save(*args, **kwargs)
        return ret


class Banner(QueueMixin, DefaultAbstract):
    bigimage = models.CharField(max_length=256, help_text='大圖')
    smallimage = models.CharField(max_length=256, null=True, help_text='小圖')
    en_bigimage = models.CharField(max_length=256, help_text='英文大圖', null=True)
    en_smallimage = models.CharField(max_length=256, null=True, help_text='英文小圖')
    link = models.CharField(max_length=256, null=True, help_text='連結')
    queue = models.SmallIntegerField(help_text='排序	TINYINT	0 ~ 255 內正整數')
    status = models.BooleanField(help_text='啟用狀態')
    display_type = models.BooleanField(help_text='上架類型')
    start_time = models.DateField(null=True, help_text='上架開始時間')
    end_time = models.DateField(null=True, help_text='上架結束時間')

    def validate(self):
        # todo 還沒有想要怎寫
        if not self.display_type:
            if self.start_time > self.end_time:
                raise

    def save(self, validate=True, *args, **kwargs):
        self.validate()
        return super().save(validate, *args, **kwargs)


class BannerContent(DefaultAbstract):
    banner = models.ForeignKey(Banner, related_name='content', on_delete=models.CASCADE,
                               help_text='首頁大圖')
    language_type = models.SmallIntegerField(help_text='語系類型 1: 中文 2: 英文')
    title = models.CharField(max_length=128, null=True, blank=True, help_text='大標題')
    subtitle = models.CharField(max_length=128, null=True, blank=True, help_text='副標題')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='敘述')
    button = models.CharField(max_length=128, null=True, blank=True, help_text='按鈕名稱')


class Permission(DefaultAbstract):
    name = models.CharField(max_length=64, help_text="角色權限名稱", unique=True)
    description = models.CharField(max_length=256, help_text="角色權限描述", null=True)
    role_manage = models.SmallIntegerField(help_text='權限編輯權限 0：無權限；1：檢視；2：編輯')
    member_manage = models.SmallIntegerField(help_text='會員管理權限 0：無權限；1：檢視；2：編輯')
    order_manage = models.SmallIntegerField(help_text='訂單管理權限 0：無權限；1：檢視；2：編輯')
    banner_manage = models.SmallIntegerField(help_text='文案管理權限 0：無權限；1：檢視；2：編輯')
    catalog_manage = models.SmallIntegerField(help_text='分類管理權限 0：無權限；1：檢視；2：編輯')
    product_manage = models.SmallIntegerField(help_text='商品管理權限 0：無權限；1：檢視；2：編輯')
    coupon_manage = models.SmallIntegerField(help_text='優惠管理權限 0：無權限；1：檢視；2：編輯')
    highest_permission = models.BooleanField(help_text='最高系統管理員', default=False)

    class Meta:
        ordering = ['-highest_permission', '-created_at']


class Manager(DefaultAbstract, AbstractBaseUser):
    permission = models.ForeignKey(Permission, related_name="manager", on_delete=models.CASCADE,
                                   help_text="權限編號")
    cn_name = models.CharField(max_length=128, help_text="中文名稱")
    en_name = models.CharField(max_length=128, help_text="英文名稱", null=True)
    email = models.EmailField(max_length=128, unique=True, help_text="電子信箱(帳號)")
    password = models.CharField(max_length=128, help_text='密碼')
    remarks = models.CharField(max_length=1024, null=True, blank=True, help_text="內部備註")
    status = models.BooleanField(help_text="啟用狀態 True：啟用；False：停用")

    def __str__(self):
        return f'{self.email} {self.cn_name}'


def default_expire_datetime():
    return timezone.now() + timezone.timedelta(minutes=15)


class Member(DefaultAbstract, AbstractBaseUser):
    member_number = models.CharField(max_length=64, help_text="會員編號 ezgo201912190000", unique=True, null=True)
    name = models.CharField(max_length=64, help_text="會員姓名")
    line_id = models.CharField(max_length=64, help_text="LINE ID", null=True)
    phone = models.CharField(max_length=64, help_text="會員電話 電話", null=True, blank=True)
    cellphone = models.CharField(max_length=64, help_text="會員手機 手機", unique=True)
    account = models.CharField(max_length=128, help_text="會員帳號", unique=True)
    password = models.CharField(max_length=128, help_text="密碼")
    remarks = models.CharField(max_length=1024, help_text="備註", null=True)
    status = models.BooleanField(help_text="啟用狀態 True：啟用；False：停用", default=True)
    default_memberaddress = models.OneToOneField('MemberAddress', default=None, null=True, help_text='預設地址',
                                                 on_delete=models.CASCADE, related_name='+')
    validate = models.BooleanField(help_text='是否已經註冊驗證', default=False)
    validate_code = models.CharField(max_length=64, help_text='驗證碼', unique=True, null=True)
    expire_datetime = models.DateTimeField(help_text='validate_code 到期時間', null=True, default=default_expire_datetime)
    in_blacklist = models.BooleanField(default=False, help_text="黑名單")
    was_in_blacklist = models.BooleanField(default=False, help_text="曾經是黑名單")
    local = models.CharField(max_length=128, help_text="會員所在地", null=True)

    def __str__(self):
        return f'{self.name}({self.id})'

    def save(self, *args, **kwargs):
        if self.in_blacklist:
            self.was_in_blacklist = True
        return super().save(*args, **kwargs)

    def set_validate_code(self):
        self.validate_code = str(uuid.uuid4())
        self.expire_datetime = default_expire_datetime()

    def get_rewards(self):
        instance = RewardRecord.objects.filter(member=self).first()
        ret = 0 if not instance else instance.total_point
        return ret

    def get_rewards_end_date(self):
        instance = RewardRecord.objects.filter(member=self).order_by('end_date').first()
        if instance is None:
            return None
        return instance.end_date

    def get_max_rewards(self, product_price):
        queryset = RewardRecord.objects.filter(member=self,
                                               use=False,
                                               start_date__lte=timezone.now().date(),
                                               end_date__gte=timezone.now().date())
        ret = 0
        for el in queryset:
            if ret + el.point < product_price:
                ret += el.point
        return ret


class BlacklistRecord(DefaultAbstract):
    member = models.ForeignKey(Member, related_name='blacklist_record', on_delete=models.CASCADE,
                               help_text='會員流水號')
    status = models.BooleanField(help_text="是否為黑名單")
    description = models.CharField(max_length=1024, help_text='標記備註', null=True)


class Category(DefaultAbstract):
    main_category = models.ForeignKey('Category', related_name='sub_categories', on_delete=models.CASCADE,
                                      help_text='母產品分類流水號', null=True)
    name = models.CharField(max_length=128, help_text="產品分類中文名稱")
    en_name = models.CharField(max_length=128, help_text="產品分類英文名稱", null=True)
    image_url = models.CharField(max_length=1024, help_text="圖片路徑", null=True)


class TagImage(DefaultAbstract):
    name = models.CharField(max_length=128, help_text='自訂標籤名稱')
    image_url = models.CharField(max_length=1024, help_text='圖片路徑')


class Tag(QueueMixin, DefaultAbstract):
    name = models.CharField(max_length=128, help_text='自訂標籤名稱')
    en_name = models.CharField(max_length=128, help_text="自訂標籤英文名稱", null=True)
    tag_image = models.ForeignKey(TagImage, related_name='tag', on_delete=models.CASCADE,
                                  help_text='圖片連結流水號')
    queue = models.IntegerField(help_text='排序', default=1)


class Brand(DefaultAbstract):
    en_name = models.CharField(max_length=128, help_text='品牌中文名稱', unique=True)
    cn_name = models.CharField(max_length=128, help_text='品牌英文名稱', null=True)
    index = models.BooleanField(help_text='是否顯示在主頁')
    menu = models.BooleanField(help_text='是否顯示在目錄')
    image_url = models.CharField(max_length=1024, help_text='圖片路徑', null=True)
    fake_id = models.IntegerField(help_text='fake_zid', null=True)


class Activity(DefaultAbstract):
    ch_name = models.CharField(max_length=256, help_text="活動中文名稱")
    en_name = models.CharField(max_length=256, help_text="活動英文名稱")
    buy_count = models.IntegerField(help_text="買多少？")
    give_count = models.IntegerField(help_text="送多少？")


class Product(DefaultAbstract):
    product_number = models.CharField(max_length=64, help_text="產品編號 P201912190000", unique=True, null=True)
    brand = models.ForeignKey(Brand, related_name='product', on_delete=models.CASCADE,
                              help_text='品牌編號', null=True)
    cn_name = models.CharField(max_length=128, help_text='產品中文名稱', null=True)
    en_name = models.CharField(max_length=128, help_text='產品英文名稱', null=True)
    order_count = models.IntegerField(help_text='訂單數量', default=0)
    cn_title = models.CharField(max_length=1024, help_text='中文標題', null=True)
    en_title = models.CharField(max_length=1024, help_text='英文標題', null=True)
    cn_sub_title = models.CharField(max_length=1024, help_text='中文副標', null=True)
    en_sub_title = models.CharField(max_length=1024, help_text='英文副標', null=True)
    description = models.TextField(help_text='商品說明', null=True)
    description_2 = models.TextField(help_text='詳細資訊', null=True)
    tag = models.ManyToManyField(Tag, related_name='product', help_text='標籤流水號')
    category = models.ManyToManyField(Category, related_name='product', help_text='分類流水號')
    cn_product_info = models.TextField(help_text='商品中文資訊', null=True, blank=True)
    cn_detail_info = models.TextField(help_text='詳細中文資訊', null=True, blank=True)
    en_product_info = models.TextField(help_text='商品英文資訊', null=True, blank=True)
    en_detail_info = models.TextField(help_text='詳細英文資訊', null=True, blank=True)
    level1_title = models.CharField(max_length=128, help_text="規則1 的主題 只有在config:product_specifications_setting",
                                    default='規格',
                                    null=True)
    level2_title = models.CharField(max_length=128, help_text="規則1 的主題 只有在config:product_specifications_setting",
                                    null=True)
    level1_en_title = models.CharField(max_length=128, help_text="規則1 的主題 只有在config:product_specifications_setting",
                                       default='規格',
                                       null=True)
    level2_en_title = models.CharField(max_length=128, help_text="規則1 的主題 只有在config:product_specifications_setting",
                                       null=True)
    status = models.BooleanField(help_text='上架狀態', default=True)
    # todo 活動?
    order = models.IntegerField(help_text='排序順序', default=1)
    activity = models.ForeignKey(Activity, related_name="product", on_delete=models.CASCADE, help_text="fk: activity",
                                 null=True)

    class Meta:
        ordering = ['order', '-updated_at', '-created_at']


class MemberWish(DefaultAbstract):
    member = models.ForeignKey(Member, related_name='memberwish', on_delete=models.CASCADE,
                               help_text='會員編號')
    product = models.ForeignKey(Product, related_name='memberwish', on_delete=models.CASCADE,
                                help_text='產品編號')


class Specification(DefaultAbstract):
    product = models.ForeignKey(Product, related_name='specifications', on_delete=models.CASCADE,
                                help_text='產品編號')
    cn_name = models.CharField(max_length=128, help_text='規格中文名稱', null=True)
    en_name = models.CharField(max_length=128, help_text='規格英文名稱', null=True)
    level = models.SmallIntegerField(help_text="LEVEL 1, 2", default=1)


class SpecificationDetail(DefaultAbstract):
    product = models.ForeignKey(Product, related_name='specifications_detail', on_delete=models.CASCADE,
                                help_text='產品編號')
    level1_spec = models.ForeignKey(Specification, related_name="specification_detail_level1", on_delete=models.CASCADE,
                                    help_text="Level 1 規格", null=True)
    level2_spec = models.ForeignKey(Specification, related_name="specification_detail_level2", on_delete=models.CASCADE,
                                    help_text="Level 2 規格", null=True)
    product_code = models.CharField(max_length=128, help_text="商品貨號", unique=True, null=True)
    # config 規格
    weight = models.FloatField(help_text='重量', null=True)
    price = models.FloatField(help_text='售價', null=None)
    fake_price = models.FloatField(help_text='原價', null=True)
    quantity = models.IntegerField(help_text='庫存量', null=True)
    inventory_status = models.SmallIntegerField(help_text='庫存狀況 0: 無庫存功能，或者是庫存使用數量表示 1：有庫存；2：無庫存；3：預購品', default=0,
                                                null=True)

    class Meta:
        ordering = ['created_at']


class Cart(DefaultAbstract):
    member = models.ForeignKey(Member, related_name='cart', on_delete=models.CASCADE,
                               help_text='會員編號')
    product = models.ForeignKey(Product, related_name='cart', on_delete=models.CASCADE,
                                help_text='產品編號')
    specification_detail = models.ForeignKey(SpecificationDetail, related_name='cart', on_delete=models.CASCADE)
    quantity = models.IntegerField(help_text='數量')


class ProductQuitShot(DefaultAbstract):
    product = models.ForeignKey(Product, related_name='productquitshot', on_delete=models.CASCADE,
                                help_text='產品編號')
    order_number = models.CharField(max_length=128, help_text='訂單編號', unique=True)
    title = models.CharField(max_length=1024, help_text='標題')
    weight = models.FloatField(help_text='重量')
    price = models.FloatField(help_text='價格')
    # todo 詳細的話該怎麼辦?
    specification = models.CharField(max_length=128, help_text='規格 用逗號隔開不同選項')
    quantity = models.IntegerField(help_text='訂購數量')


class ProductImage(DefaultAbstract):
    product = models.ForeignKey(Product, related_name='productimages', on_delete=models.CASCADE,
                                help_text='產品編號')
    image_url = models.CharField(max_length=1024, help_text='圖片路徑', null=True)
    main_image = models.BooleanField(help_text='是否為主圖', default=False)
    specification = models.ForeignKey(Specification,
                                      related_name="product_image",
                                      on_delete=models.CASCADE, help_text="規格的圖片", null=True)

    class Meta:
        ordering = ['-main_image', '-created_at']


class MemberStore(DefaultAbstract):
    member = models.ForeignKey(Member, related_name='memberstore', on_delete=models.CASCADE,
                               help_text='會員編號')
    # ECPAY
    sub_type = models.CharField(max_length=32, help_text="FAMI、UNIMART、HILIFE", null=True)
    store_id = models.CharField(max_length=32, help_text="ECPAY:store id 非ECPAY:分店店號")
    store_name = models.CharField(max_length=32, help_text="ECPAY:store name 非ECPAY:分店名稱")
    address = models.CharField(max_length=64, help_text="address")
    phone = models.CharField(max_length=32, help_text="phone", null=True)


class MemberAddress(DefaultAbstract):
    member = models.ForeignKey(Member, related_name='memberaddress', on_delete=models.CASCADE,
                               help_text='會員編號')
    shipping_name = models.CharField(max_length=64, help_text="收貨人姓名", null=True)
    phone = models.CharField(max_length=64, help_text="收貨人電話", null=True)
    shipping_address = models.CharField(max_length=64, help_text="宅配", null=True)
    shipping_area = models.CharField(max_length=64, help_text="郵遞區號", null=True)
    location = models.SmallIntegerField(help_text="地區: 1：國內 2: 國外", default=1)
    # ---- 國外 only ----
    first_name = models.CharField(max_length=64, help_text="First Name(海外)", null=True)
    last_name = models.CharField(max_length=64, help_text="Last Name(海外)", null=True)
    country = models.CharField(max_length=64, help_text="Country", null=True)
    building = models.CharField(max_length=64, help_text="大樓名字(海外)", null=True)
    company_name = models.CharField(max_length=64, help_text="公司名字(海外)", null=True)
    city = models.CharField(max_length=64, help_text="City(海外)", null=True)
    postal_code = models.CharField(max_length=64, help_text="Postal (海外)", null=True)

    class Meta:
        ordering = ['created_at']


class Order(DefaultAbstract):
    member = models.ForeignKey(Member, related_name='order', on_delete=models.CASCADE,
                               help_text='會員編號')
    shipping_name = models.CharField(max_length=64, help_text="收貨人姓名", null=True)
    total_price = models.IntegerField(help_text='總計', default=0)
    freeshipping_price = models.IntegerField(help_text='運費', default=0)
    product_price = models.IntegerField(help_text='商品售價', default=0)
    coupon_price = models.IntegerField(help_text='折價費用', default=0)
    reward_price = models.IntegerField(help_text='忠誠獎勵', default=0)
    activity_price = models.IntegerField(help_text='活動折抵', default=0)
    total_weight = models.FloatField(help_text='總重量', default=0)
    coupon = models.ForeignKey('Coupon', related_name='order', on_delete=models.CASCADE, help_text='使用的Coupon',
                               null=True)
    payment_type = models.CharField(max_length=64, help_text='付款方式', null=True, default='未付款')
    order_number = models.CharField(max_length=64, help_text="訂單編號", unique=True, null=True)
    phone = models.CharField(max_length=64, help_text="會員電話", null=True)
    product_shot = models.TextField(help_text='products simple json str', null=True)
    bussiness_number = models.CharField(max_length=64, help_text="統編", null=True)
    company_title = models.CharField(max_length=64, help_text="抬頭", null=True)
    address = models.CharField(max_length=64, help_text="地址", null=True)
    shipping_address = models.CharField(max_length=64, help_text="宅配", null=True)
    shipping_area = models.CharField(max_length=64, help_text="郵遞區號", null=True)
    pay_status = models.SmallIntegerField(help_text='1: 已付款 0: 未付款', default=0)
    pay_type = models.SmallIntegerField(help_text='1: 貨到付款 0: 線上付款', default=0)
    take_number = models.SmallIntegerField(help_text='1: 取號成功 0: 取號失敗', default=0)
    shipping_status = models.IntegerField(help_text='shipping map', null=True)
    simple_status = models.IntegerField(help_text="簡單對status 做分類", null=True, default=1)
    simple_status_display = models.CharField(max_length=64, help_text="簡單對status 做分類: 1: 待出貨; 2: 付款失敗; 3: 取號成功; 4: 取號失敗; 5: 已取消",
                                             null=True, default='未付款')
    use_ecpay_delivery = models.BooleanField(default=True, help_text="使用ecpay 的物流機制")
    # --- only 國外 ---
    location = models.SmallIntegerField(help_text="地區: 1：國內 2: 國外", default=1)
    first_name = models.CharField(max_length=64, help_text="First Name(海外)", null=True)
    last_name = models.CharField(max_length=64, help_text="Last Name(海外)", null=True)
    country = models.CharField(max_length=64, help_text="Country", null=True)
    building = models.CharField(max_length=64, help_text="大樓名字(海外)", null=True)
    company_name = models.CharField(max_length=64, help_text="公司名字(海外)", null=True)
    city = models.CharField(max_length=64, help_text="City(海外)", null=True)
    postal_code = models.CharField(max_length=64, help_text="Postal (海外)", null=True)
    # -----------------

    to_store = models.BooleanField(help_text="超商取貨: True 宅配: False", default=False)
    store_type = models.CharField(max_length=64, help_text='超商種類', null=True)
    store_id = models.CharField(max_length=64, help_text='超商ID', null=True)
    cancel_order = models.BooleanField(default=False, help_text='取消訂單')
    order_remark = models.TextField(help_text="訂單備註", null=True)
    remark = models.TextField(help_text="內部備註", null=True)
    remark_date = models.DateTimeField(help_text="內部備註時間", null=True)
    ecpay_data = models.TextField(help_text='ECPAY RETURN DATA', null=True)
    store_name = models.CharField(max_length=32, help_text="store name", null=True)
    all_pay_logistics_id = models.CharField(max_length=64, help_text='物流交易編號', null=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        from api.sdk.ecpay import payment_type
        simple_status_display = shipping_map.simple_display_mapping.get(str(self.shipping_status))
        if simple_status_display == '已取消':
            self.simple_status = 5
        if simple_status_display:
            self.simple_status_display = simple_status_display
        if self.payment_type in payment_type.keys():
            self.payment_type = payment_type[self.payment_type]
        return super().save()


class FreeShipping(DefaultAbstract):
    backstage_name = models.CharField(max_length=256, help_text='後台名字')
    frontend_name = models.CharField(max_length=256, help_text='前台名字')
    cn_title = models.CharField(max_length=256, help_text='免運中文標語', null=True)
    en_title = models.CharField(max_length=256, help_text='免運英文標語', null=True)
    cash_on_delivery = models.SmallIntegerField(help_text="貨到付款")
    role = models.IntegerField(help_text='免運門檻')
    weight = models.IntegerField(help_text='免運限制', null=True)
    price = models.IntegerField(help_text='運費金額')
    # 店家的代號 之前的設計 名字不改掉 不然要改掉的部分太多
    sub_type = models.CharField(max_length=128, help_text='店家的代號 ex: FAMI', null=True)
    enable = models.BooleanField(default=True, help_text="開啟功能")
    location = models.SmallIntegerField(help_text="地區: 1：國內 2: 國外", default=1)
    use_ecpay_delivery = models.BooleanField(default=True, help_text="使用ecpay 的物流機制")


class Coupon(DefaultAbstract):
    role = models.IntegerField(help_text='折價門檻')
    method = models.SmallIntegerField(help_text='折價方式 1: 元 2: 百分比')
    discount = models.IntegerField(help_text='折價金額, 折價折數')
    cn_title = models.CharField(max_length=128, help_text='中文標題')
    en_title = models.CharField(max_length=128, help_text='英文標題')
    discount_code = models.CharField(max_length=32, help_text='折價券序號', unique=True)
    image_url = models.CharField(max_length=1024, help_text='圖片路徑')
    en_image_url = models.CharField(max_length=1024, help_text='英文圖片路徑', null=True)
    start_time = models.DateField(help_text='啟用日期', null=True)
    end_time = models.DateField(help_text='到期日期', null=True)
    has_period = models.BooleanField(default=False, help_text="有使用期限")
    has_member_use_limit = models.BooleanField(default=False, help_text="會員使用限制次數限制")
    member_use_limit = models.IntegerField(help_text="會員使用限制次數", null=True)
    has_coupon_use_limit = models.BooleanField(default=False, help_text="優換券使用限制次數限制")
    coupon_use_limit = models.IntegerField(help_text="優換券使用限制次數", null=True)
    has_member_list = models.BooleanField(default=False, help_text="針對會員開放")
    member = models.ManyToManyField(Member, related_name='coupon', help_text='會員流水號')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        """
        Trigger 如果哪邊有資料就算沒有改狀態也要自動幫他改
        """
        if not self.id:
            return super().save(force_insert, force_update, using, update_fields)
        if self.member.count():
            self.has_member_list = True
        # if self.start_time or self.end_time:
        #     self.has_period = True
        if self.member_use_limit is not None:
            self.has_member_use_limit = True
        if self.coupon_use_limit is not None:
            self.has_coupon_use_limit = True
        return super().save(force_insert, force_update, using, update_fields)

    def get_status(self, user):
        """
        1: 正常
        2: 過期
        3: 超過個人使用限制
        4: 超過全體使用限制
        """
        instance = self
        now = timezone.now().date()
        ret = 1
        period_status = instance.start_time <= now < instance.end_time if instance.has_period else True
        if not period_status:
            ret = 2
            return ret

        in_member_use_limit = instance.order.filter(
            member=user).count() < instance.member_use_limit \
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


class Reward(DefaultAbstract):
    status = models.SmallIntegerField(help_text='回饋方式 1: 元 2: 百分比')
    pay_to = models.IntegerField(help_text='status=1時, 達到多少錢回饋', null=True)
    discount = models.IntegerField(help_text='回饋金額, 回饋百分比')
    still_day = models.IntegerField(help_text='期限')
    start_day = models.IntegerField(help_text='忠誠獎勵發放天數 發送時間 n day 之後')


class RewardRecord(DefaultAbstract):
    member = models.ForeignKey(Member, related_name='reward', on_delete=models.CASCADE,
                               help_text='會員流水號')
    order = models.ForeignKey(Order, related_name='rewrad', on_delete=models.CASCADE,
                              null=True, help_text='訂單流水號|可能是手動或是系統產生')
    desc = models.CharField(max_length=256, help_text="回饋金備註", default='購物回饋點數')
    manual = models.BooleanField(default=False, help_text="手動新增")
    point = models.IntegerField(help_text='回饋點數')
    total_point = models.IntegerField(help_text='回饋點數總共餘額')
    end_date = models.DateField(help_text='期限｜根據config 決定是單筆還是統一更新', null=True)
    use_point = models.IntegerField(default=0, help_text='已使用回饋點數')

    def check_config(self):
        """
        feeback_money_setting: 會員回饋金 1: 沒有回饋金功能 2: 回饋期限日期統一 3: 依造訂單設定回饋日期
        """
        from .util import get_config
        config = get_config()
        # 統一就要把所有的一起改成一樣
        if config['feeback_money_setting'] == 2:
            for instance in RewardRecord.objects.all():
                instance.end_date = self.end_date
                instance.save()


class RewardRecordTemp(DefaultAbstract):
    """
    存在RewardRecord 的是真的已經入帳的資料預計入帳的資料會顯示在這邊
    """
    start_date = models.DateField(help_text='期限｜根據config 決定是什麼時候更新到RewardRecord')
    end_date = models.DateField(help_text='期限｜根據config 決定是單筆還是統一更新')
    member = models.ForeignKey(Member, related_name='reward_temp', on_delete=models.CASCADE,
                               help_text='會員流水號')
    order = models.ForeignKey(Order, related_name='rewrad_temp', on_delete=models.CASCADE,
                              null=True, help_text='訂單流水號|可能是手動或是系統產生')
    desc = models.CharField(max_length=256, help_text="回饋金備註", default='購物回饋點數')
    point = models.IntegerField(help_text='回饋點數')


class ConfigSetting(DefaultAbstract):
    # 商品庫存
    product_stock_setting = models.SmallIntegerField(help_text="商品庫存 1: 沒有庫存功能 2: 只有庫存文案顯示 3: 完整庫存功能")
    # 商品規格
    product_specifications_setting = models.SmallIntegerField(help_text="商品規格 1: 只有規格名稱 2: 詳細規格(兩層)")
    # 重量
    weight = models.BooleanField(help_text="是否顯示重量")
    # 會員回饋金
    feeback_money_setting = models.SmallIntegerField(help_text="會員回饋金 1: 沒有回饋金功能 2: 回饋期限日期統一 3: 依造訂單設定回饋日期")
    activity = models.BooleanField(default=False, help_text="活動： 買幾送幾")
    in_maintenance = models.BooleanField(default=False, help_text="維護中")


class Country(DefaultAbstract):
    name = models.CharField(max_length=128, help_text="國家名字")
