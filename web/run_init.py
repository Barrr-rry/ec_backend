import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')
django.setup()
from django.contrib.auth.models import User
from api import serializers
from django.utils import timezone
from api.models import Banner, BannerContent, Permission, AdminTokens, Manager, Member, Category, Brand, Product, \
    ProductImage, Tag, Specification, TagImage, MemberTokens, FreeShipping, Coupon, Reward, Order, RewardRecord, \
    Cart, MemberAddress, MemberWish, ConfigSetting, SpecificationDetail, Country, RewardRecordTemp, Activity
import datetime
import random
from fake_data import cn_name, en_name, get_random_letters, get_random_number, banner_args, categories, brands
import json
from django.utils.timezone import make_aware
from munch import Munch
from dateutil.relativedelta import relativedelta

fmt = '%Y-%m-%d %H:%M:%S'
test_email = 'max@conquers.co'

categories_mapping = {
    '其他成分': ['CoQ-10 輔酵素',
             'DHEA 脫氫異雄固酮',
             'DMAE 二甲氨乙醇',
             'MSM 甲基磺酰甲烷',
             '七酮基脫氫表雄酮',
             '二十二碳六烯酸',
             '二十碳五烯酸',
             '亞麻籽',
             '人蔘',
             '共軛亞麻油酸',
             '南瓜籽油',
             '卵磷脂',
             '多酚 / 茶多酚',
             '大蒜精',
             '對乙酰氨基酚',
             '山桑子',
             '山楂果',
             '布洛芬',
             '月見草油',
             '朝鮮薊',
             '植物甾醇/烷醇',
             '泛酸',
             '洋車前子',
             '消化酵素',
             '玻尿酸',
             '瓜氨酸',
             '生物素',
             '番茄紅素 / 茄紅素',
             '白藜蘆醇',
             '石榴',
             '硒質',
             '硫辛酸',
             '碧蘿芷',
             '磷蝦油',
             '精氨酸',
             '紅麴',
             '納豆',
             '紫錐花',
             '綠茶精華',
             '維生素 A (β-胡蘿蔔素)',
             '維生素 B',
             '維生素 C',
             '維生素 D',
             '維生素 E',
             '維生素 K',
             '纖維質',
             '聖潔莓',
             '聖約翰草',
             '肉桂',
             '肌醇',
             '胺基丁酸',
             '膠原蛋白',
             '茶氨酸',
             '萘普生鈉',
             '葫蘆巴',
             '蒲公英根',
             '蔓越莓',
             '薑黃',
             '藍莓',
             '蝦青素 / 蝦紅素',
             '螺旋藻',
             '軟骨素',
             '過氧化氫酶',
             '鉀質',
             '鋅質',
             '鎂質',
             '鐵質',
             '阿斯匹靈',
             '離胺酸',
             '馬卡',
             '麩醯胺酸',
             '黑升麻', ],
}


def main(for_test=False, config_data=None):
    if config_data is None:
        with open('./config.json') as f:
            config_data = json.loads(f.read())

    config_data = Munch(config_data)
    ConfigSetting.objects.create(**config_data)
    from api.util import pickle_redis
    pickle_redis.remove_data('configsetting')

    generate_super_admin()
    generate_permissions()
    generate_super_manager(email=test_email, password='1111')
    generate_managers(20)
    generate_brands()
    generate_categories()
    generate_tags()
    if for_test:
        generate_products_for_test(20, config_data)
    else:
        generate_products_for_test(30, config_data)
    generate_members_with_token()
    generate_members(20)
    generate_banners(10)
    generate_freeshipping()
    generate_coupon(10)
    generate_orders()
    for member in Member.objects.all():
        generate_reward(member, 3)
    generate_cart()
    genearete_country()
    generate_activity(config_data)


def generate_activity(config_data):
    if not config_data.activity:
        return

    instance = Activity.objects.create(
        ch_name='買二送一',
        en_name='buy 2 give 1',
        buy_count=2,
        give_count=1,
    )
    queryset = Product.objects.all()
    for i in range(5):
        pd = random.choice(queryset)
        pd.activity = instance
        pd.save()


def generate_super_admin():
    from django.contrib.auth.models import User

    # create admin
    if not User.objects.first():
        user = User.objects.create_user('admin', password='1111')
        user.is_superuser = True
        user.is_staff = True
        user.save()


def generate_cart():
    member = Member.objects.filter(account=test_email).first()
    queryset = Product.objects.all()
    product = queryset[0]
    if not member or not product:
        return
    Cart.objects.create(
        member=member,
        product=product,
        specification_detail=product.specifications_detail.first(),
        quantity=1
    )
    product = queryset.last()
    product.status = False
    product.save()
    Cart.objects.create(
        member=member,
        product=product,
        specification_detail=product.specifications_detail.first(),
        quantity=1
    )


def generate_reward(member, count):
    record = Reward.objects.create(status=1, discount=100, still_day=30, start_day=7, pay_to=100)
    orders = Order.objects.filter(member=member).all()
    for order in orders:
        point = random.randint(1, 100)
        RewardRecordTemp.objects.create(
            member=member,
            order=order,
            point=point,
            end_date=timezone.now() + timezone.timedelta(days=record.still_day),
            start_date=timezone.now()
        )
    for i in range(count):
        point = random.randint(1, 100)
        temp = RewardRecord.objects.filter(member=member).first()
        RewardRecord.objects.create(
            member=member,
            desc='手動新增回饋點數',
            manual=1,
            point=point,
            end_date=timezone.now() + timezone.timedelta(days=record.still_day),
            total_point=temp.total_point + point if temp else point,
        )


def generate_orders():
    member = Member.objects.filter(account=test_email).first()
    if not member:
        return
    now = datetime.datetime.now()
    seq = [True, False]
    for i in range(50 + 1):
        order = Order.objects.create(
            shipping_name='maxwang',
            order_number=f'M{get_random_number(8)}',
            total_price=random.choice(range(1, 10000)),
            freeshipping_price=random.choice(range(1, 10000)),
            product_price=random.choice(range(1, 10000)),
            coupon_price=random.choice(range(1, 10000)),
            reward_price=random.choice(range(1, 10000)),
            total_weight=random.choice(range(1, 10000)),
            phone='0922111333',
            product_shot='[{"id": 30, "product_number": "P2020052929", "brand_en_name": "GNC", "brand_cn_name": "\\u5065\\u5b89\\u559c", "tag": [], "tag_detail": [], "category": [72], "tag_name": null, "categories": [{"id": 72, "sub_categories": [], "has_product": true, "name": "\\u795e\\u7d93\\u7cfb\\u7d71\\u529f\\u80fd", "en_name": null, "image_url": "efficacy/a-06.svg", "main_category": 67}], "productimages": [{"main_image": true, "image_url": "default-banner-smallimage.png", "specification": null}, {"main_image": false, "image_url": "default-banner-smallimage.png", "specification": null}], "specifications_detail": [{"id": 531, "spec1_name": "B", "spec2_name": "RGB\\u4e09\\u539f\\u8272", "product_code": "8305511366", "weight": 0.6, "price": 314.0, "fake_price": 213.0, "quantity": 3, "inventory_status": 0, "product": 30, "level1_spec": 260, "level2_spec": 266}, {"id": 532, "spec1_name": "B", "spec2_name": "White", "product_code": "5032427117", "weight": 0.6, "price": 956.0, "fake_price": 213.0, "quantity": 2, "inventory_status": 0, "product": 30, "level1_spec": 260, "level2_spec": 267}, {"id": 533, "spec1_name": "B", "spec2_name": "Yello", "product_code": "3117810016", "weight": 0.6, "price": 478.0, "fake_price": 213.0, "quantity": 3, "inventory_status": 0, "product": 30, "level1_spec": 260, "level2_spec": 268}, {"id": 534, "spec1_name": "C", "spec2_name": "RGB\\u4e09\\u539f\\u8272", "product_code": "0549156667", "weight": 0.6, "price": 209.0, "fake_price": 213.0, "quantity": 8, "inventory_status": 0, "product": 30, "level1_spec": 261, "level2_spec": 266}, {"id": 535, "spec1_name": "C", "spec2_name": "White", "product_code": "1358559295", "weight": 0.6, "price": 650.0, "fake_price": 213.0, "quantity": 5, "inventory_status": 0, "product": 30, "level1_spec": 261, "level2_spec": 267}, {"id": 536, "spec1_name": "C", "spec2_name": "Yello", "product_code": "8336628371", "weight": 0.6, "price": 133.0, "fake_price": 213.0, "quantity": 8, "inventory_status": 0, "product": 30, "level1_spec": 261, "level2_spec": 268}, {"id": 537, "spec1_name": "S", "spec2_name": "RGB\\u4e09\\u539f\\u8272", "product_code": "9205211365", "weight": 0.6, "price": 318.0, "fake_price": 213.0, "quantity": 0, "inventory_status": 0, "product": 30, "level1_spec": 262, "level2_spec": 266}, {"id": 538, "spec1_name": "S", "spec2_name": "White", "product_code": "0709308330", "weight": 0.6, "price": 829.0, "fake_price": 213.0, "quantity": 9, "inventory_status": 0, "product": 30, "level1_spec": 262, "level2_spec": 267}, {"id": 539, "spec1_name": "S", "spec2_name": "Yello", "product_code": "8808112966", "weight": 0.6, "price": 181.0, "fake_price": 213.0, "quantity": 6, "inventory_status": 0, "product": 30, "level1_spec": 262, "level2_spec": 268}, {"id": 540, "spec1_name": "L", "spec2_name": "RGB\\u4e09\\u539f\\u8272", "product_code": "5684927567", "weight": 0.6, "price": 750.0, "fake_price": 213.0, "quantity": 6, "inventory_status": 0, "product": 30, "level1_spec": 263, "level2_spec": 266}, {"id": 541, "spec1_name": "L", "spec2_name": "White", "product_code": "8534554573", "weight": 0.6, "price": 167.0, "fake_price": 213.0, "quantity": 9, "inventory_status": 0, "product": 30, "level1_spec": 263, "level2_spec": 267}, {"id": 542, "spec1_name": "L", "spec2_name": "Yello", "product_code": "8057256887", "weight": 0.6, "price": 782.0, "fake_price": 213.0, "quantity": 2, "inventory_status": 0, "product": 30, "level1_spec": 263, "level2_spec": 268}, {"id": 543, "spec1_name": "D", "spec2_name": "RGB\\u4e09\\u539f\\u8272", "product_code": "7923136996", "weight": 0.6, "price": 639.0, "fake_price": 213.0, "quantity": 10, "inventory_status": 0, "product": 30, "level1_spec": 264, "level2_spec": 266}, {"id": 544, "spec1_name": "D", "spec2_name": "White", "product_code": "8181506622", "weight": 0.6, "price": 740.0, "fake_price": 213.0, "quantity": 4, "inventory_status": 0, "product": 30, "level1_spec": 264, "level2_spec": 267}, {"id": 545, "spec1_name": "D", "spec2_name": "Yello", "product_code": "8586278327", "weight": 0.6, "price": 299.0, "fake_price": 213.0, "quantity": 10, "inventory_status": 0, "product": 30, "level1_spec": 264, "level2_spec": 268}, {"id": 546, "spec1_name": "XL", "spec2_name": "RGB\\u4e09\\u539f\\u8272", "product_code": "2329731174", "weight": 0.6, "price": 913.0, "fake_price": 213.0, "quantity": 4, "inventory_status": 0, "product": 30, "level1_spec": 265, "level2_spec": 266}, {"id": 547, "spec1_name": "XL", "spec2_name": "White", "product_code": "8262499309", "weight": 0.6, "price": 709.0, "fake_price": 213.0, "quantity": 5, "inventory_status": 0, "product": 30, "level1_spec": 265, "level2_spec": 267}, {"id": 548, "spec1_name": "XL", "spec2_name": "Yello", "product_code": "4288346389", "weight": 0.6, "price": 490.0, "fake_price": 213.0, "quantity": 2, "inventory_status": 0, "product": 30, "level1_spec": 265, "level2_spec": 268}], "specifications": [{"id": 268, "name": "Yello", "level": 2, "product": 30}, {"id": 267, "name": "White", "level": 2, "product": 30}, {"id": 266, "name": "RGB\\u4e09\\u539f\\u8272", "level": 2, "product": 30}, {"id": 265, "name": "XL", "level": 1, "product": 30}, {"id": 264, "name": "D", "level": 1, "product": 30}, {"id": 263, "name": "L", "level": 1, "product": 30}, {"id": 262, "name": "S", "level": 1, "product": 30}, {"id": 261, "name": "C", "level": 1, "product": 30}, {"id": 260, "name": "B", "level": 1, "product": 30}], "status_display": "\\u4e0a\\u67b6\\u4e2d", "inventory_status_display": "\\u7121\\u5eab\\u5b58", "specifications_quantity": "0~10", "activity_detail": null, "name": "\\u9ed1\\u4eba\\u982d\\u5167\\u893229", "order_count": 1, "title": "title", "sub_title": "sub_title", "description": null, "description_2": null, "product_info": "<div class=\\"red\\">\\u5305\\u8ca8\\u6642\\u672c\\u516c\\u53f8\\u53ef\\u80fd\\u6703\\u9700\\u8981\\u5c07\\u5916\\u76d2\\u62c6\\u9664\\uff0c\\u4ee5\\u65b9\\u4fbf\\u904b\\u9001\\uff0c\\u7522\\u54c1\\u54c1\\u8cea\\u5c07\\u4e0d\\u53d7\\u5f71\\u97ff\\u3002\\u7522\\u54c1\\u904b\\u9001\\u6642\\u53ef\\u80fd\\u56e0\\u6a5f\\u4e0a\\u8259\\u58d3\\u800c\\u9020\\u6210\\u7522\\u54c1\\u6e17\\u6f0f\\uff0c\\u7531\\u65bc\\u9019\\u9ede\\u672c\\u516c\\u53f8\\u7121\\u6cd5\\u63a7\\u5236\\uff0c\\u56e0\\u6b64\\u7121\\u6cd5\\u505a\\u4efb\\u4f55\\u8ce0\\u511f\\uff0c\\u656c\\u8acb\\u898b\\u8ad2\\u3002</div><div class=\\"red\\">\\u8a02\\u8cfc\\u8d85\\u904e 12 \\u74f6\\u7684\\u8cb7\\u5bb6\\uff0c\\u8acb\\u5206\\u958b\\u4e0b\\u55ae\\uff0c\\u4e26\\u63d0\\u4f9b\\u591a\\u500b\\u6536\\u4ef6\\u4eba\\u8cc7\\u6599\\uff0c\\u672c\\u516c\\u53f8\\u6703\\u5354\\u52a9\\u5c07\\u5305\\u88f9\\u5206\\u958b\\u5bc4\\u51fa\\u3002</div><p>\\u7522\\u54c1\\u7c21\\u4ecb</p><p>\\u7f8e\\u570b\\u597d\\u5e02\\u591a Costco \\u7368\\u5bb6\\u92b7\\u552e\\u7684 KirkLand 5% Minoxidil \\u751f\\u9aee\\u6c34\\u6240\\u542b\\u7684\\u6210\\u4efd\\u8207\\u843d\\u5065 5% \\u5f37\\u6548\\u751f\\u9aee\\u6c34\\u76f8\\u540c\\uff0c\\u5c0d\\u65bc\\u7d93\\u5e38\\u4f7f\\u7528\\u4e14\\u4e0d\\u60f3\\u82b1\\u5927\\u9322\\u7684\\u4eba\\u4f86\\u8aaa\\u662f\\u500b\\u4e0d\\u932f\\u7684\\u9078\\u64c7\\u3002</p><li>\\u7121\\u8272\\u7121\\u5473</li><li>\\u6bcf\\u7f50\\u5bb9\\u91cf \\uff1a 60ml</li><li>\\u542b\\u6709 5% \\u7684 Minoxidil</li><li>\\u5be6\\u9a57\\u8b49\\u660e\\u80fd\\u5e6b\\u52a9\\u982d\\u9aee\\u91cd\\u65b0\\u751f\\u9577</li><li>\\u6709\\u6548\\u523a\\u6fc0\\u6bdb\\u56ca\\uff0c\\u5e6b\\u52a9\\u6bdb\\u56ca\\u518d\\u5ea6\\u751f\\u9577</li><li>\\u901a\\u5e38\\u5728 2 ~ 4 \\u500b\\u6708\\u5c31\\u53ef\\u4ee5\\u770b\\u5230\\u6210\\u6548</li><li>\\u50f9\\u683c\\u6bd4\\u540c\\u6548\\u679c\\u7684\\u843d\\u5065\\u66f4\\u70ba\\u5212\\u7b97</li><li>\\u6b64\\u7522\\u54c1\\u70ba\\u7537\\u6027\\u5c08\\u7528\\uff0c\\u5973\\u6027\\u4e0d\\u53ef\\u4f7f\\u7528</li><p>&nbsp;</p><p>Kirkland \\u751f\\u9aee\\u6c34\\u7684\\u6709\\u6548\\u6210\\u5206\\u70ba 5% \\u7684 Minoxidil ( \\u7c73\\u8afe\\u5730\\u723e )\\uff0cMinoxidil \\u662f\\u76ee\\u524d\\u552f\\u4e00\\u88ab\\u7f8e\\u570b FDA \\u8a8d\\u8b49\\u6709\\u6548\\u7684\\u5916\\u7528\\u751f\\u9aee\\u7522\\u54c1\\uff0c\\u5df2\\u6709\\u5145\\u5206\\u7684\\u81e8\\u5e8a\\u8a66\\u9a57\\u8b49\\u5be6\\u7c73\\u8afe\\u5730\\u723e\\u5c0d\\u96c4\\u6fc0\\u7d20\\u6027\\u812b\\u9aee\\uff08 \\u907a\\u50b3\\u578b\\u812b\\u9aee\\u3001\\u8102\\u6ea2\\u578b\\u812b\\u9aee \\uff09\\uff0c\\u6591\\u79bf\\u7b49\\u90fd\\u6709\\u8f03\\u597d\\u7684\\u7642\\u6548\\u3002</p><em><i>*\\u9019\\u4e9b\\u8072\\u660e\\u5c1a\\u672a\\u7d93\\u904e\\u7f8e\\u570b\\u98df\\u54c1\\u548c\\u85e5\\u7269\\u7ba1\\u7406\\u5c40\\u8a55\\u4f30\\u3002\\u672c\\u7522\\u54c1\\u4e0d\\u80fd\\u7528\\u65bc\\u8a3a\\u65b7\\uff0c\\u6cbb\\u7642\\uff0c\\u6cbb\\u7652\\u6216\\u9810\\u9632\\u4efb\\u4f55\\u75be\\u75c5\\u3002</i></em><p>&nbsp;</p><figure class=\\"table\\"><table><tbody><tr><td colspan=\\"2\\">&nbsp;<strong>\\u7522\\u54c1\\u898f\\u683c</strong>&nbsp;</td></tr><tr><td>\\u88fd\\u9020\\u5ee0\\u5546</td><td>&nbsp;Costco Wholesale Corporation</td></tr><tr><td>&nbsp;\\u88fd\\u9020\\u7522\\u5730</td><td>\\u4ee5\\u8272\\u5217&nbsp;</td></tr><tr><td>\\u4fdd\\u5b58\\u671f\\u9650&nbsp;</td><td>\\u65b0\\u8ca8 \\u4fdd\\u5b58\\u671f\\u9650\\u5230 2021 \\u5e74 1 \\u6708&nbsp;</td></tr><tr><td>\\u7522\\u54c1\\u5bb9\\u91cf&nbsp;</td><td>6 \\u74f6 x 60 ml - ( \\u5171\\u516d\\u500b\\u6708\\u4efd\\u91cf &nbsp;)</td></tr><tr><td>\\u7522\\u54c1\\u91cd\\u91cf&nbsp;</td><td>1.3 \\u78c5&nbsp;</td></tr><tr><td>\\u7522\\u54c1\\u9ad4\\u7a4d&nbsp;</td><td>\\u539f\\u5ee0\\u5305\\u88dd ( \\u82f1\\u5bf8 ) : 6 x 5.5 x 3&nbsp;</td></tr></tbody></table></figure>", "detail_info": "<p><strong>\\u4f7f\\u7528\\u65b9\\u5f0f :</strong></p><li>\\u6bcf\\u5929\\u5728\\u812b\\u9aee\\u5340\\u57df\\u7528\\u6ef4\\u6db2\\u7ba1\\u6ef4\\u5169\\u6b21\\uff0c\\u6bcf\\u6b21 1 mL</li><li>\\u4f7f\\u7528\\u66f4\\u591a\\u5291\\u91cf\\u6216\\u66f4\\u591a\\u6b21\\u6578\\u4e0d\\u6703\\u6709\\u4efb\\u4f55\\u5e6b\\u52a9</li><li>\\u6301\\u7e8c\\u4f7f\\u7528\\u624d\\u80fd\\u78ba\\u4fdd\\u982d\\u9aee\\u6301\\u7e8c\\u518d\\u751f\\uff0c\\u4e0d\\u7136\\u812b\\u9aee\\u6703\\u518d\\u6b21\\u51fa\\u73fe</li><figure class=\\"table\\"><table><tbody><tr><td colspan=\\"2\\"><strong>Drug Facts ( \\u85e5\\u7269\\u6210\\u4efd\\u8868 )</strong></td></tr><tr><td colspan=\\"2\\"><strong>Active Ingredient ( \\u6d3b\\u6027\\u6210\\u5206 )</strong></td></tr><tr><td>Minoxidil 5% w/v ( \\u7c73\\u8afe\\u5730\\u723e )</td><td>Hair regrowth treatment for men ( \\u7537\\u6027\\u982d\\u9aee\\u518d\\u751f\\u6cbb\\u7642 )</td></tr><tr><td colspan=\\"2\\"><strong>USE</strong> to regrow hair on the top of the scalp ( vertex only )<br>\\u6548\\u7528 : \\u5e6b\\u52a9\\u9802\\u90e8\\u982d\\u9aee\\u518d\\u751f\\uff08 \\u50c5\\u9069\\u7528\\u65bc\\u9aee\\u6e26\\u6027\\u79bf\\u982d\\uff09</td></tr><tr><td colspan=\\"2\\"><strong>Warnings ( \\u8b66\\u544a )</strong><br><strong>For external use only, For use by men only</strong><br><strong>( \\u50c5\\u4f9b\\u5916\\u90e8\\u4f7f\\u7528\\uff0c\\u50c5\\u4f9b\\u7537\\u6027\\u4f7f\\u7528 )</strong><br><strong>Flammable:</strong> keep away from fire or flame<br><strong>( \\u6613\\u71c3\\uff1a\\u9060\\u96e2\\u706b\\u6e90\\u6216\\u706b\\u7130 )</strong></td></tr><tr><td colspan=\\"2\\"><p><strong>Do not use if ( \\u5982\\u6709\\u4ee5\\u4e0b\\u72c0\\u6cc1\\u8acb\\u505c\\u6b62\\u4f7f\\u7528 )</strong></p><li>you are woman ( \\u4f60\\u662f\\u5973\\u59d3 )</li><li>your amount of hair loss is different than that shown on the side of this carton or your hair loss is on the front of the scalp. Minoxidil topical solution 5 % is not intended for frontal balness or receding hairline. ( \\u4f60\\u7684\\u812b\\u9aee\\u91cf\\u8207\\u9019\\u500b\\u7d19\\u6838\\u5074\\u9762\\u5716\\u6848\\u4e0a\\u986f\\u793a\\u7684\\u4e0d\\u540c\\uff0c\\u6216\\u8005\\u4f60\\u7684\\u812b\\u9aee\\u662f\\u5728\\u524d\\u9762\\u90e8\\u4f4d\\u3002 \\u7c73\\u8afe\\u5730\\u723e\\u4e0d\\u9069\\u7528\\u65bc\\u524d\\u79bf\\u6216\\u9000\\u5f8c\\u9aee\\u7dda\\u3002 )</li><li>you have no family history of hair loss ( \\u5bb6\\u65cf\\u88e1\\u6c92\\u6709\\u5176\\u4ed6\\u6210\\u54e1\\u6709\\u843d\\u9aee\\u73fe\\u8c61\\u51fa\\u73fe )</li><li>your hair loss is sudden and/or patchy ( \\u4f60\\u7684\\u812b\\u9aee\\u662f\\u7a81\\u7136\\u767c\\u751f \\u548c/\\u6216 \\u51fa\\u73fe\\u7247\\u72c0\\u843d\\u9aee )</li><li>you do not know the reason for your hair loss ( \\u4f60\\u4e0d\\u77e5\\u9053\\u843d\\u9aee\\u539f\\u56e0 )</li><li>you are under 18 years of age. do not use on babies and children ( \\u672a\\u6eff 18\\u6b72\\uff0c\\u4e0d\\u53ef\\u4f7f\\u7528\\u65bc\\u5b30\\u5152\\u6216\\u5152\\u7ae5 )</li><li>your scalp is red, inflamed, infected, irritated, or painful ( \\u60a8\\u7684\\u982d\\u76ae\\u767c\\u7d05\\u3001\\u767c\\u708e\\u3001\\u611f\\u67d3\\u3001\\u523a\\u75db \\u6216\\u75bc\\u75db\\u611f )</li><li>you use other medicines on the scalp ( \\u982d\\u76ae\\u4e0a\\u4f7f\\u7528\\u5176\\u4ed6\\u85e5\\u7269 )</li></td></tr><tr><td colspan=\\"2\\"><strong>Ask a doctor before use if you have heart disease</strong><br><strong>( \\u5982\\u679c\\u60a8\\u60a3\\u6709\\u5fc3\\u9ad2\\u75c5\\uff0c\\u8acb\\u5728\\u4f7f\\u7528\\u524d\\u8a62\\u554f\\u91ab\\u751f )</strong></td></tr><tr><td colspan=\\"2\\"><p><strong>When using this product ( \\u4f7f\\u7528\\u9019\\u9805\\u7522\\u54c1\\u6642 )</strong></p><li>do not apply on other parts of the body ( \\u8acb\\u52ff\\u4f7f\\u7528\\u5728\\u5176\\u4ed6\\u8eab\\u9ad4\\u90e8\\u4f4d )</li><li>avoid contact with the eyes. In case of accidental contact, rinse eyes with large amounts of cool tap water. ( \\u8acb\\u907f\\u514d\\u63a5\\u89f8\\u773c\\u775b\\u3002 \\u842c\\u4e00\\u610f\\u5916\\u63a5\\u89f8\\uff0c\\u8acb\\u91cf\\u76e1\\u5feb\\u4f7f\\u7528\\u5927\\u91cf\\u51b7\\u6c34\\u6c96\\u6d17\\u773c\\u775b\\u3002 )</li><li>some people have experienced changes in hair color and/or texture ( \\u90e8\\u4efd\\u4f7f\\u7528\\u8005\\u51fa\\u73fe\\u9aee\\u8272\\u548c\\u9aee\\u8cea\\u7684\\u8b8a\\u5316 )</li><li>it takes time to regrow hair. Results may occur at 2 months with twice a day usage. For some men, you may need to use this product at least 4 months before you see results. ( \\u751f\\u9aee\\u9700\\u8981\\u6642\\u9593\\u3002\\u6bcf\\u65e5\\u4f7f\\u7528\\u5169\\u6b21\\u7684\\u4f7f\\u7528\\u8005\\u901a\\u5e38\\u9700\\u89812\\u500b\\u6708\\u7684\\u6642\\u9593\\u624d\\u6703\\u770b\\u5230\\u6210\\u6548\\u3002\\u800c\\u90e8\\u4efd\\u7537\\u58eb\\u53ef\\u80fd\\u9700\\u8981\\u81f3\\u5c114\\u500b\\u6708\\u624d\\u80fd\\u770b\\u5230\\u6548\\u679c\\u3002 )</li><li>the amount of hair regrowth is different for each person. This product will not work for all men ( \\u6bcf\\u4eba\\u982d\\u9aee\\u518d\\u751f\\u7684\\u60c5\\u6cc1\\u4e0d\\u540c\\u3002\\u672c\\u7522\\u54c1\\u4e0d\\u9069\\u5408\\u6240\\u6709\\u7537\\u58eb\\u4f7f\\u7528 )</li></td></tr><tr><td colspan=\\"2\\"><p><strong>Stop use and ask a doctor if ( \\u767c\\u751f\\u4ee5\\u4e0b\\u60c5\\u6cc1\\u8acb\\u505c\\u6b62\\u4f7f\\u7528\\u4e26\\u8a62\\u554f\\u5c08\\u696d\\u91ab\\u5e2b )</strong></p><li>chest pain, rapid heartbeat, fantness, or dizziness occurs ( \\u80f8\\u75db\\uff0c\\u5fc3\\u8df3\\u52a0\\u5feb\\uff0c\\u6688\\u53a5\\u6216\\u7729\\u6688 )</li><li>sudden, unexplained weight gain occurs ( \\u7a81\\u7136\\u767c\\u751f\\u3001\\u4e0d\\u660e\\u539f\\u56e0\\u7684\\u9ad4\\u91cd\\u589e\\u52a0 )</li><li>your hands or feet swell ( \\u4f60\\u7684\\u624b\\u6216\\u8173\\u816b\\u8139 )</li><li>scalp irritation or redness occurs ( \\u767c\\u751f\\u982d\\u76ae\\u523a\\u75db\\u6216\\u767c\\u7d05 )</li><li>unwanted facial hair growth occurs ( \\u51fa\\u73fe\\u4e0d\\u9700\\u8981\\u7684\\u6bdb\\u9aee\\u751f\\u9577 )</li><li>you do not see hair regrowth in 4 month ( 4 \\u500b\\u6708\\u5167\\u770b\\u4e0d\\u5230\\u982d\\u9aee\\u518d\\u5ea6\\u751f\\u9577 )</li></td></tr><tr><td colspan=\\"2\\"><strong>May be harmful if used when pregnant or breast-feeding. ( \\u61f7\\u5b55\\u6216\\u54fa\\u4e73\\u6642\\u4f7f\\u7528\\u53ef\\u80fd\\u6709\\u5bb3 )</strong><br><strong>keep out of reach of children.</strong>if swallowed, get medical help or contact a Poison Control center right away (<strong> \\u9060\\u96e2\\u5152\\u7ae5</strong>\\u3002\\u5982\\u679c\\u541e\\u56a5\\uff0c\\u8acb\\u99ac\\u4e0a\\u5c0b\\u6c42\\u91ab\\u7642\\u5e6b\\u52a9 )</td></tr><tr><td colspan=\\"2\\"><p><strong>Directions ( \\u4f7f\\u7528\\u65b9\\u5f0f )</strong></p><li>apply one mL with dropper 2 times a day directly onto the scalp in the hair loss area ( \\u6bcf\\u5929\\u5728\\u812b\\u9aee\\u5340\\u57df\\u7528\\u6ef4\\u6db2\\u7ba1\\u6ef4\\u5169\\u6b21\\uff0c\\u6bcf\\u6b21 1 mL)</li><li>using more or more often will not improve result ( \\u4f7f\\u7528\\u66f4\\u591a\\u5291\\u91cf\\u6216\\u66f4\\u591a\\u6b21\\u6578\\u4e0d\\u6703\\u6709\\u4efb\\u4f55\\u5e6b\\u52a9 )</li><li>continued use is necessary to increase and keep your hair regrowth, or hair loss will begin again ( \\u6301\\u7e8c\\u4f7f\\u7528\\u624d\\u80fd\\u78ba\\u4fdd\\u982d\\u9aee\\u6301\\u7e8c\\u518d\\u751f\\uff0c\\u4e0d\\u7136\\u812b\\u9aee\\u6703\\u518d\\u6b21\\u51fa\\u73fe )</li></td></tr><tr><td colspan=\\"2\\"><p><strong>Other informantion ( \\u5176\\u4ed6\\u8cc7\\u6599 )</strong></p><li>see hair loss pictures on the side of this carton ( \\u8acb\\u770b\\u7d19\\u76d2\\u5074\\u9762\\u7684\\u812b\\u9aee\\u5716\\u7247 )</li><li>before use, read all information on carton and enclosed leaflet ( \\u4f7f\\u7528\\u524d\\u8acb\\u95b1\\u8b80\\u5916\\u76d2\\u4e0a\\u7684\\u8cc7\\u8a0a\\u4ee5\\u53ca\\u9644\\u5e36\\u7684\\u8aaa\\u660e\\u66f8 )</li><li>keep the carton. it contains important information ( \\u4fdd\\u7559\\u7d19\\u76d2\\u3002 \\u5b83\\u5305\\u542b\\u4e86\\u91cd\\u8981\\u4fe1\\u606f )</li><li>hair regrowth has not been shown to last longer than 48 weeks in large clinical trials with continuous treatment with minoxidil topical solution 5 % for men ( \\u5728\\u5927\\u898f\\u6a21\\u81e8\\u5e8a\\u8a66\\u9a57\\u4e2d\\uff0c\\u9023\\u7e8c\\u7528 5% \\u7c73\\u8afe\\u5730\\u723e\\u6cbb\\u7642\\u7684\\u5be6\\u9a57\\u8005\\uff0c\\u982d\\u9aee\\u518d\\u751f\\u9577\\u671f\\u6c92\\u6709\\u8d85\\u904e48\\u9031 )</li><li>in clinical studies with mostly white men aged 18-49 years of moderate degress of hair loss, minoxidil topical solution 5% for men provided more hair regrowth than minoxidil topical solution 2% ( \\u5728\\u81e8\\u5e8a\\u8a66\\u9a57\\u4e2d\\uff0c\\u5927\\u90e8\\u4efd\\u7684\\u5be6\\u9a57\\u5c0d\\u8c61\\u5927\\u591a\\u70ba\\u767d\\u4eba\\uff0c\\u5e74\\u8a18 18\\u523049\\u6b72\\uff0c\\u64c1\\u6709\\u4e2d\\u7b49\\u7a0b\\u5ea6\\u7684\\u812b\\u9aee\\u3002\\u5be6\\u9a57\\u8b49\\u660e 5% \\u7684\\u7c73\\u8afe\\u5730\\u723e\\u6548\\u679c\\u6bd4 2% \\u7684\\u9084\\u8981\\u6709\\u6548\\u3002 )</li><li>store at 20\\u00b0 to 25\\u00b0C (68\\u00b0 to 77\\u00b0F). keep tightly closed. (\\u8acb\\u4fdd\\u5b58\\u65bc 20\\u00b0C \\u81f3 25\\u00b0C\\uff08 68\\u00b0 \\u81f3 77 \\u00b0F \\uff09\\u7684\\u6eab\\u5ea6\\u5167\\uff0c\\u4e26\\u4fdd\\u6301\\u84cb\\u5b50\\u5bc6\\u9589\\u3002 )</li></td></tr><tr><td colspan=\\"2\\"><strong>Inactive ingredients ( \\u975e\\u6d3b\\u6027\\u6210\\u5206 )</strong> alcohol ( \\u9152\\u7cbe ), propylene glycol ( \\u4e19\\u4e8c\\u9187 ), purified water( \\u6de8\\u5316\\u6c34 )</td></tr></tbody></table></figure><p>&nbsp;</p>", "level1_title": "\\u5c3a\\u5bf8", "level2_title": "\\u984f\\u8272", "status": true, "order": 1, "brand": 12, "activity": null, "specification_detail": {"id": 531, "spec1_name": "B", "spec2_name": "RGB\\u4e09\\u539f\\u8272", "product_code": "8305511366", "weight": 0.6, "price": 314.0, "fake_price": 213.0, "quantity": 3, "inventory_status": 0, "product": 30, "level1_spec": 260, "level2_spec": 266}, "quantity": 1}]',
            address='台北市中正區中山南路７號１樓',
            shipping_address='台北市中正區中山南路７號１樓',
            pay_status=1,
            pay_type=1,
            shipping_status='300',
            simple_status=1,
            simple_status_display='待出貨',
            to_store=random.choice(seq),
            store_type='FAMI',
            store_id='006598',
            store_name='假的店名',
            member=member,
            shipping_area='888'
        )
        # 不同時間為了測試時間區間
        order.created_at = make_aware(now + datetime.timedelta(days=random.choice(range(-20, 20))))
        order.save()

    rewardrecord = RewardRecord.objects.create(
        end_date=timezone.now() + timezone.timedelta(days=10),
        order=order,
        member=member,
        desc='購物回饋點數',
        point=100,
        total_point=100,
    )


def generate_permissions():
    permission = Permission.objects.create(name='高級管理員', description='超級管理員什麼都可以做', role_manage=2, member_manage=2,
                                           order_manage=2, banner_manage=2, catalog_manage=2, product_manage=2,
                                           coupon_manage=2, highest_permission=True)
    permission = Permission.objects.create(name='一般管理員', description='主管 可以部分修改編輯', role_manage=2, member_manage=2,
                                           order_manage=2, banner_manage=2, catalog_manage=2, product_manage=2,
                                           coupon_manage=2)
    permission = Permission.objects.create(name='基礎檢視身份', description='出貨小妹 只能看', role_manage=1, member_manage=1,
                                           order_manage=1, banner_manage=1, catalog_manage=1, product_manage=1,
                                           coupon_manage=1)


def generate_super_manager(email, password, name='中文姓名', key=None):
    """
    :param email:
    :param password:
    :param name:
    :param key: 如果None 則是 password
    :return:
    """
    if key is None:
        key = password
    permission = Permission.objects.filter(name='高級管理員').first()
    manager = Manager(email=email, password=password, status=True, cn_name=name, en_name=name,
                      permission=permission)
    manager.set_password(manager.password)
    manager.created_at = timezone.now()
    manager.save()
    # default key
    AdminTokens.objects.create(user=manager, key=key)


def generate_managers(count):
    permissions = Permission.objects.all()
    for i in range(count):
        manager = Manager(email=f'${get_random_letters(random.choice(range(10, 15)))}@conquers.co', password='1111',
                          status=True, cn_name=random.choice(cn_name), en_name=random.choice(en_name),
                          permission=random.choice(permissions))
        manager.set_password(manager.password)
        manager.created_at = timezone.now()
        manager.save()


def generate_members_with_token():
    member = Member.objects.create(
        member_number="member_1111",
        name='Max',
        phone=f'02-7774444#5532',
        cellphone=f'0923123456',
        account=test_email,
        password='1111',
        remarks='HI',
        validate=True,
        local='台灣'
    )
    member.set_password('1111')
    member.save()
    MemberTokens.objects.create(user=member, key='11111')
    memberaddress = MemberAddress.objects.create(
        member=member,
        shipping_name='MaxWang',
        phone='0926017837',
        shipping_address='中正四路100號',
        shipping_area='802',
    )
    member.default_memberaddress = memberaddress
    member.save()

    for pd in Product.objects.all()[:10]:
        MemberWish.objects.create(
            member=member,
            product=pd
        )


def generate_members(count):
    for i in range(count):
        number_count = random.choice(range(5, 10))
        prefix_email = get_random_letters(random.choice(range(10, 15)))
        now = datetime.datetime.now()
        bir = (now - relativedelta(years=int(random.randint(0, 100)))).strftime('%Y-%m-%d')
        wei = random.randint(50, 100)
        hei = random.randint(160, 190)
        bmi = wei / pow((hei / 100), 2)
        member = Member.objects.create(
            member_number=f"hfmu${get_random_number(number_count)}",
            name=random.choice(cn_name),
            phone=f'02-{get_random_number(8)}',
            cellphone=f'09{get_random_number(8)}',
            account=f'{prefix_email}@gmail.com',
            password='abc123',
            remarks='HI',
            status=random.choice([True, False]),
            email_status=random.choice([True, False]),
            validate=True,
            local=random.choice(['海外', '台灣']),
            gender=random.choice([1, 2]),
            birthday=bir,
            weight=wei,
            height=hei,
            bmi=bmi
        )
        member.set_password('abc123')
        member.save()


def generate_banners(count):
    index = 0
    generate_content = lambda language: dict(title=None,
                                             subtitle=None,
                                             description=None,
                                             language_type=1 if language == 'CH' else 2,
                                             button=None)
    for i in range(1, count + 1):
        banner_arg = random.choice(banner_args)
        banner = Banner.objects.create(
            bigimage='banner.png',
            link='https://li1871-48.members.linode.com/',
            queue=i,
            status=True,
            **banner_arg
        )
        banner_content_1 = BannerContent.objects.create(
            banner=banner,
            **generate_content('CH')
        )

        banner_content_2 = BannerContent.objects.create(
            banner=banner,
            **generate_content('EN')
        )


def generate_categories():
    categories = ['商品總覽',
                  '三角內褲',
                  '四角內褲',
                  '比基尼三角',
                  '提臀內褲',
                  '周邊商品']
    all_categories = ['熱銷商品',
                      '材質分類',
                      '顏色分類']
    for category in categories:
        Category.objects.create(
            name=category
        )
    all_category = Category.objects.filter(name='商品總覽').first()
    for category in all_categories:
        Category.objects.create(
            main_category=all_category,
            name=category
        )
    material_category = Category.objects.filter(name='材質分類').first()
    Category.objects.create(
        main_category=material_category,
        name='洞洞彈性',
        image_url='材質icon_洞洞彈性.svg'
    )
    Category.objects.create(
        main_category=material_category,
        name='純棉',
        image_url='材質icon_純棉.svg'
    )


def generate_tags():
    tag_image_1 = TagImage.objects.create(name='一般-綠', image_url='label-green')
    tag_image_2 = TagImage.objects.create(name='一般-紅', image_url='label-red')
    tag_image_3 = TagImage.objects.create(name='一般-藍', image_url='label-blue')
    Tag.objects.create(name='熱銷商品', tag_image=tag_image_1, queue=1)
    Tag.objects.create(name='新品上市', tag_image=tag_image_2, queue=2)
    Tag.objects.create(name='好評不斷', tag_image=tag_image_3, queue=3)


def generate_brands():
    # images = [
    #     'logo-1.png',
    #     'logo-2.png',
    #     'logo-3.png',
    #     'logo-4.png',
    #     'logo-5.png',
    #     'logo-6.png',
    # ]
    # for i in range(len(brands)):
    #     params = dict(
    #         en_name=brands[i],
    #         cn_name=cn_name[i],
    #         index=False,
    #         menu=random.choice([True, False]),
    #         fake_id=-i
    #     )
    #     if images:
    #         params['index'] = True
    #         params['image_url'] = images.pop()
    #     Brand.objects.create(**params)
    with open('./data/brands.json') as f:
        brands = json.load(f)
    fake_id = 0
    for el in brands:
        Brand.objects.create(
            en_name=el['en_name'],
            cn_name=el['ch_name'],
            index=random.choice([True, False]),
            menu=random.choice([True, False]),
            image_url=el['image'],
            fake_id=fake_id,
        )
        fake_id += 1


def generate_product_image():
    return f'product{random.randint(1, 3)}.png'


def generate_products_for_test(count, config_data):
    spec_level1 = ['紅色', '藍色', '黃色', '綠色', '白色', '黑色']
    spec_level2 = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']
    tag = Tag.objects.all()
    brand = Brand.objects.all()
    category = Category.objects.exclude(name='商品總覽').all()
    all_category = Category.objects.filter(name='商品總覽').first()
    now = timezone.now().strftime('%Y%m%d')
    activity = Activity.objects.first()
    for i in range(count):

        dct = dict(
            product_number=f'P{now}{i}',
            brand=random.choice(brand),
            name=f'黑人頭內褲{i}',
            title='title',
            sub_title='sub_title',
            product_info="""<div class="red">包貨時本公司可能會需要將外盒拆除，以方便運送，產品品質將不受影響。產品運送時可能因機上艙壓而造成產品渗漏，由於這點本公司無法控制，因此無法做任何賠償，敬請見諒。</div><div class="red">訂購超過 12 瓶的買家，請分開下單，並提供多個收件人資料，本公司會協助將包裹分開寄出。</div><p>產品簡介</p><p>美國好市多 Costco 獨家銷售的 KirkLand 5% Minoxidil 生髮水所含的成份與落健 5% 強效生髮水相同，對於經常使用且不想花大錢的人來說是個不錯的選擇。</p><li>無色無味</li><li>每罐容量 ： 60ml</li><li>含有 5% 的 Minoxidil</li><li>實驗證明能幫助頭髮重新生長</li><li>有效刺激毛囊，幫助毛囊再度生長</li><li>通常在 2 ~ 4 個月就可以看到成效</li><li>價格比同效果的落健更為划算</li><li>此產品為男性專用，女性不可使用</li><p>&nbsp;</p><p>Kirkland 生髮水的有效成分為 5% 的 Minoxidil ( 米諾地爾 )，Minoxidil 是目前唯一被美國 FDA 認證有效的外用生髮產品，已有充分的臨床試驗證實米諾地爾對雄激素性脫髮（ 遺傳型脫髮、脂溢型脫髮 ），斑禿等都有較好的療效。</p><em><i>*這些聲明尚未經過美國食品和藥物管理局評估。本產品不能用於診斷，治療，治癒或預防任何疾病。</i></em><p>&nbsp;</p><figure class="table"><table><tbody><tr><td colspan="2">&nbsp;<strong>產品規格</strong>&nbsp;</td></tr><tr><td>製造廠商</td><td>&nbsp;Costco Wholesale Corporation</td></tr><tr><td>&nbsp;製造產地</td><td>以色列&nbsp;</td></tr><tr><td>保存期限&nbsp;</td><td>新貨 保存期限到 2021 年 1 月&nbsp;</td></tr><tr><td>產品容量&nbsp;</td><td>6 瓶 x 60 ml - ( 共六個月份量 &nbsp;)</td></tr><tr><td>產品重量&nbsp;</td><td>1.3 磅&nbsp;</td></tr><tr><td>產品體積&nbsp;</td><td>原廠包裝 ( 英寸 ) : 6 x 5.5 x 3&nbsp;</td></tr></tbody></table></figure>""",
            detail_info="""<p><strong>使用方式 :</strong></p><li>每天在脫髮區域用滴液管滴兩次，每次 1 mL</li><li>使用更多劑量或更多次數不會有任何幫助</li><li>持續使用才能確保頭髮持續再生，不然脫髮會再次出現</li><figure class="table"><table><tbody><tr><td colspan="2"><strong>Drug Facts ( 藥物成份表 )</strong></td></tr><tr><td colspan="2"><strong>Active Ingredient ( 活性成分 )</strong></td></tr><tr><td>Minoxidil 5% w/v ( 米諾地爾 )</td><td>Hair regrowth treatment for men ( 男性頭髮再生治療 )</td></tr><tr><td colspan="2"><strong>USE</strong> to regrow hair on the top of the scalp ( vertex only )<br>效用 : 幫助頂部頭髮再生（ 僅適用於髮渦性禿頭）</td></tr><tr><td colspan="2"><strong>Warnings ( 警告 )</strong><br><strong>For external use only, For use by men only</strong><br><strong>( 僅供外部使用，僅供男性使用 )</strong><br><strong>Flammable:</strong> keep away from fire or flame<br><strong>( 易燃：遠離火源或火焰 )</strong></td></tr><tr><td colspan="2"><p><strong>Do not use if ( 如有以下狀況請停止使用 )</strong></p><li>you are woman ( 你是女姓 )</li><li>your amount of hair loss is different than that shown on the side of this carton or your hair loss is on the front of the scalp. Minoxidil topical solution 5 % is not intended for frontal balness or receding hairline. ( 你的脫髮量與這個紙核側面圖案上顯示的不同，或者你的脫髮是在前面部位。 米諾地爾不適用於前禿或退後髮線。 )</li><li>you have no family history of hair loss ( 家族裡沒有其他成員有落髮現象出現 )</li><li>your hair loss is sudden and/or patchy ( 你的脫髮是突然發生 和/或 出現片狀落髮 )</li><li>you do not know the reason for your hair loss ( 你不知道落髮原因 )</li><li>you are under 18 years of age. do not use on babies and children ( 未滿 18歲，不可使用於嬰兒或兒童 )</li><li>your scalp is red, inflamed, infected, irritated, or painful ( 您的頭皮發紅、發炎、感染、刺痛 或疼痛感 )</li><li>you use other medicines on the scalp ( 頭皮上使用其他藥物 )</li></td></tr><tr><td colspan="2"><strong>Ask a doctor before use if you have heart disease</strong><br><strong>( 如果您患有心髒病，請在使用前詢問醫生 )</strong></td></tr><tr><td colspan="2"><p><strong>When using this product ( 使用這項產品時 )</strong></p><li>do not apply on other parts of the body ( 請勿使用在其他身體部位 )</li><li>avoid contact with the eyes. In case of accidental contact, rinse eyes with large amounts of cool tap water. ( 請避免接觸眼睛。 萬一意外接觸，請量盡快使用大量冷水沖洗眼睛。 )</li><li>some people have experienced changes in hair color and/or texture ( 部份使用者出現髮色和髮質的變化 )</li><li>it takes time to regrow hair. Results may occur at 2 months with twice a day usage. For some men, you may need to use this product at least 4 months before you see results. ( 生髮需要時間。每日使用兩次的使用者通常需要2個月的時間才會看到成效。而部份男士可能需要至少4個月才能看到效果。 )</li><li>the amount of hair regrowth is different for each person. This product will not work for all men ( 每人頭髮再生的情況不同。本產品不適合所有男士使用 )</li></td></tr><tr><td colspan="2"><p><strong>Stop use and ask a doctor if ( 發生以下情況請停止使用並詢問專業醫師 )</strong></p><li>chest pain, rapid heartbeat, fantness, or dizziness occurs ( 胸痛，心跳加快，暈厥或眩暈 )</li><li>sudden, unexplained weight gain occurs ( 突然發生、不明原因的體重增加 )</li><li>your hands or feet swell ( 你的手或腳腫脹 )</li><li>scalp irritation or redness occurs ( 發生頭皮刺痛或發紅 )</li><li>unwanted facial hair growth occurs ( 出現不需要的毛髮生長 )</li><li>you do not see hair regrowth in 4 month ( 4 個月內看不到頭髮再度生長 )</li></td></tr><tr><td colspan="2"><strong>May be harmful if used when pregnant or breast-feeding. ( 懷孕或哺乳時使用可能有害 )</strong><br><strong>keep out of reach of children.</strong>if swallowed, get medical help or contact a Poison Control center right away (<strong> 遠離兒童</strong>。如果吞嚥，請馬上尋求醫療幫助 )</td></tr><tr><td colspan="2"><p><strong>Directions ( 使用方式 )</strong></p><li>apply one mL with dropper 2 times a day directly onto the scalp in the hair loss area ( 每天在脫髮區域用滴液管滴兩次，每次 1 mL)</li><li>using more or more often will not improve result ( 使用更多劑量或更多次數不會有任何幫助 )</li><li>continued use is necessary to increase and keep your hair regrowth, or hair loss will begin again ( 持續使用才能確保頭髮持續再生，不然脫髮會再次出現 )</li></td></tr><tr><td colspan="2"><p><strong>Other informantion ( 其他資料 )</strong></p><li>see hair loss pictures on the side of this carton ( 請看紙盒側面的脫髮圖片 )</li><li>before use, read all information on carton and enclosed leaflet ( 使用前請閱讀外盒上的資訊以及附帶的說明書 )</li><li>keep the carton. it contains important information ( 保留紙盒。 它包含了重要信息 )</li><li>hair regrowth has not been shown to last longer than 48 weeks in large clinical trials with continuous treatment with minoxidil topical solution 5 % for men ( 在大規模臨床試驗中，連續用 5% 米諾地爾治療的實驗者，頭髮再生長期沒有超過48週 )</li><li>in clinical studies with mostly white men aged 18-49 years of moderate degress of hair loss, minoxidil topical solution 5% for men provided more hair regrowth than minoxidil topical solution 2% ( 在臨床試驗中，大部份的實驗對象大多為白人，年記 18到49歲，擁有中等程度的脫髮。實驗證明 5% 的米諾地爾效果比 2% 的還要有效。 )</li><li>store at 20° to 25°C (68° to 77°F). keep tightly closed. (請保存於 20°C 至 25°C（ 68° 至 77 °F ）的溫度內，並保持蓋子密閉。 )</li></td></tr><tr><td colspan="2"><strong>Inactive ingredients ( 非活性成分 )</strong> alcohol ( 酒精 ), propylene glycol ( 丙二醇 ), purified water( 淨化水 )</td></tr></tbody></table></figure><p>&nbsp;</p>""",
        )
        if config_data.activity:
            dct['activity'] = activity
        product = Product.objects.create(
            **dct
        )
        if i % 2 == 0:
            product.tag.add(random.choice(tag))
        product.category.add(random.choice(category))
        product.category.add(all_category)
        product.save()
        ProductImage.objects.create(
            product=product,
            image_url=generate_product_image(),
            main_image=True,
        )
        ProductImage.objects.create(
            product=product,
            image_url=generate_product_image(),
            main_image=False,
        )
        # 規格細節
        if config_data.product_specifications_setting == 2:
            # 規格1, 規格2
            product.level1_title = '顏色'
            product.level2_title = '尺寸'
            product.level1_en_title = 'color'
            product.level2_en_title = 'size'
            product.save()
            colors = ['Blue', 'Red', 'Yello', 'White', 'RGB三原色']
            sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']
            random.shuffle(sizes)
            random.shuffle(colors)
            spec1_list = []
            spec2_list = []
            for color in colors[:random.randint(1, len(colors))]:
                spec1_list.append(
                    Specification.objects.create(
                        product=product,
                        name=color,
                        level=1,
                    )
                )
            for size in sizes[:random.randint(1, len(sizes))]:
                spec2_list.append(
                    Specification.objects.create(
                        product=product,
                        name=size,
                        level=2,
                    )
                )
            for spec1 in spec1_list:
                for spec2 in spec2_list:
                    # config data
                    number_count = random.choice(range(5, 10))
                    weight = 0.6 if config_data.weight else None
                    price = random.randint(100, 1000)
                    fake_price = 213
                    inventory_status = 0 if config_data.product_stock_setting != 2 else random.randint(1, 3)
                    quantity = None if config_data.product_stock_setting != 3 else random.randint(0, 10)

                    SpecificationDetail.objects.create(
                        product=product,
                        level1_spec=spec1,
                        level2_spec=spec2,
                        product_code=f'{get_random_number(10)}',
                        weight=weight,
                        price=price,
                        fake_price=fake_price,
                        quantity=quantity,
                        inventory_status=inventory_status,
                    )

                    # 只有規格名稱
        elif config_data.product_specifications_setting == 1:
            for i in range(1, random.randint(2, 4)):
                # config data
                number_count = random.choice(range(5, 10))
                weight = 0.6 if config_data.weight else None
                price = random.randint(100, 1000)
                fake_price = 213
                inventory_status = 0 if config_data.product_stock_setting != 2 else random.randint(1, 3)
                quantity = None if config_data.product_stock_setting != 3 else random.randint(0, 10)

                spec1 = Specification.objects.create(
                    product=product,
                    name=f'一般{i if i != 1 else ""}',
                )
                SpecificationDetail.objects.create(
                    product=product,
                    level1_spec=spec1,
                    product_code=f'{get_random_number(10)}',
                    weight=weight,
                    price=price,
                    fake_price=fake_price,
                    quantity=quantity,
                    inventory_status=inventory_status,
                )


def generate_products_ezgo(config_data):
    """
    # todo ezgo ganerate product 要改成這個
    這個其實是for EZGO 才需要的
    """
    import json
    from pprint import pprint as pp
    import math
    Product.objects.all().delete()

    with open('./data/categories.json') as f:
        categories = json.load(f)
    with open('./data/products.json') as f:
        products = json.load(f)
    now = timezone.now().strftime('%Y%m%d')
    tag = Tag.objects.all()
    i = 0
    for el in products:
        i += 1
        if not el:
            continue
        brand = Brand.objects.filter(en_name=el['brand']).first()

        instance = Product.objects.create(
            product_number=f'P{now}{i}',
            brand=brand,
            name=el['name'],
            sub_title=None,
            weight=math.ceil(el['weight'] * 453.59237) / 1000,
            price=el['price'],
            fake_price=None,
            product_info=el['product_info'],
            detail_info=el['detail_info'],
            quantity=random.randint(0, 100)
        )
        if i % 2 == 0:
            instance.tag.add(random.choice(tag))
        Specification.objects.create(
            product=instance,
            name='一般',
        )
        ProductImage.objects.create(
            product=instance,
            image_url=el['main_image'].strip('./'),
            main_image=True,
        )
        for img in el['images']:
            if not img:
                continue
            ProductImage.objects.create(
                product=instance,
                image_url=img.strip('./'),
                main_image=False,
            )
    for key, val in categories.items():
        for mkey, mval in categories_mapping.items():
            if key in mval:
                key = mkey
        category = Category.objects.filter(name=key).first()
        if category is None:
            continue
        for name in val:
            instance = Product.objects.filter(name=name).first()
            instance.category.add(category)


def generate_freeshipping():
    oversea = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='10', price=60,
        cash_on_delivery=False, frontend_name='DHL', backstage_name='海外（DHL）', location=2,
        use_ecpay_delivery=False,
    )
    oversea = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='5', price=60,
        cash_on_delivery=False, frontend_name='EMS', backstage_name='海外（EMS）', location=2,
        use_ecpay_delivery=False,
    )
    oversea = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='3', price=60,
        cash_on_delivery=False, frontend_name='郵寄', backstage_name='海外（郵寄）', location=2,
        use_ecpay_delivery=False,
    )
    store = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='5', price=65,
        cash_on_delivery=True, frontend_name='OK 超商', backstage_name='超商取貨（OK 超商）',
        sub_type=None, location=1,
        use_ecpay_delivery=False,

    )
    store = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='5', price=65,
        cash_on_delivery=True, frontend_name='7-11', backstage_name='超商取貨（7-11）',
        sub_type='UNIMART', location=1,
        use_ecpay_delivery=True,
    )
    store = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='5', price=65,
        cash_on_delivery=True, frontend_name='萊爾富(免運推薦)', backstage_name='超商取貨（萊爾富）',
        sub_type='HILIFE', location=1,
        use_ecpay_delivery=True,
    )
    store = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='5', price=65,
        cash_on_delivery=True, frontend_name='全家(免運推薦)', backstage_name='超商取貨（全家）',
        sub_type='FAMI', location=1,
        use_ecpay_delivery=True,
    )
    home_delivery = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='999', price=90,
        cash_on_delivery=False, frontend_name='宅配到府', backstage_name='宅配到府', location=1,
        use_ecpay_delivery=False,
    )


def generate_coupon(count):
    for i in range(count):
        day = random.randint(-20, 20)
        Coupon.objects.create(
            role=random.randint(0, 100),
            method=random.choice([1, 2]),
            discount=random.randint(0, 100),
            title=f'折價券{i}',
            discount_code=f'DC{get_random_number(7)}',
            image_url='11697.jpg',
            start_time=timezone.now() + timezone.timedelta(days=day - 10),
            end_time=timezone.now() + timezone.timedelta(days=day),
        )


def genearete_country():
    names = ['美國', '日本', '大陸']
    for name in names:
        Country.objects.create(name=name)


if __name__ == '__main__':
    main()
