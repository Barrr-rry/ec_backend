import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'web.settings')
django.setup()
from django.contrib.auth.models import User
from api import serializers
from django.utils import timezone
from api.models import Banner, BannerContent, Permission, AdminTokens, Manager, Member, Category, Brand, Product, \
    ProductImage, Tag, Specification, TagImage, MemberTokens, FreeShipping, Coupon, Reward, Order, RewardRecord, \
    Cart, MemberAddress, MemberWish, ConfigSetting, SpecificationDetail
import datetime
import random
from fake_data import cn_name, en_name, get_random_letters, get_random_number, banner_args, categories, brands
import json
from munch import Munch

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

    generate_super_admin()
    generate_permissions()
    generate_super_manager(email=test_email, password='1111')
    generate_managers(20)
    generate_brands()
    generate_categories()
    generate_tags()
    generate_products_for_test(2, config_data)
    generate_members_with_token()
    generate_members(20)
    generate_banners(10)
    generate_freeshipping()
    generate_coupon(10)
    generate_reward()
    generate_orders()
    generate_cart()


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
    product = Product.objects.first()
    if not member or not product:
        return
    Cart.objects.create(
        member=member,
        product=product,
        specification=product.specifications.first(),
        quantity=1
    )


def generate_reward():
    Reward.objects.create(status=1, discount=100, still_day=30)


def generate_orders():
    member = Member.objects.filter(account=test_email).first()
    if not member:
        return
    order = Order.objects.create(
        shipping_name='maxwang',
        order_number='M202002100604091',
        total_price=200,
        freeshipping_price=200,
        product_price=200,
        coupon_price=200,
        reward_price=200,
        total_weight=200,
        phone='0922111333',
        product_shot='[{"id": 96, "product_number": "P2020021095", "brand_en_name": "Balanceuticals", "brand_cn_name": "\u9673\u80e4\u798e", "category_name": "\u5b55\u5a66\u8207\u5bf6\u5bf6", "name": "\u9280\u5bf6\u5584\u5b5895", "title": "title", "sub_title": "sub_title", "weight": 2312.0, "price": 123.0, "fake_price": 213.0, "inventory_status": 2, "description": null, "description_2": null, "brand": 19, "tag": null, "category": 26, "productimages": [{"id": 191, "image_url": "default-banner-smallimage.png", "main_image": true, "product": 96}, {"id": 192, "image_url": "default-banner-bigimage.png", "main_image": false, "product": 96}], "specifications": [{"id": 192, "name": "201", "product": 96}, {"id": 191, "name": "200", "product": 96}], "specification": {"id": 192, "name": "201", "product": 96}, "quantity": 1}]',
        address='台北市中正區中山南路７號１樓',
        shipping_address='台北市中正區中山南路７號１樓',
        pay_status=1,
        pay_type=1,
        shipping_status='300',
        simple_status=1,
        simple_status_display='待出貨',
        to_store=True,
        store_type='FAMI',
        store_id='006598',
        store_name='假的店名',
        member=member,
        shipping_area='888'
    )

    rewardrecord = RewardRecord.objects.create(
        start_date=timezone.now() - timezone.timedelta(days=10),
        end_date=timezone.now() + timezone.timedelta(days=10),
        order=order,
        member=member,
        point=100,
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
        member = Member.objects.create(
            member_number=f"ezgo${get_random_number(number_count)}",
            name=random.choice(cn_name),
            phone=f'02-{get_random_number(8)}',
            cellphone=f'09{get_random_number(8)}',
            account=f'{prefix_email}@gmail.com',
            password='abc123',
            remarks='HI',
            status=random.choice([True, False]),
            validate=True,
        )
        member.set_password('abc123')
        member.save()


def generate_banners(count):
    index = 0
    generate_content = lambda language: dict(title=f'{language}_title',
                                             subtitle=f'{language}_subtitle',
                                             description=f'{language}_description',
                                             language_type=1 if language == 'CH' else 2,
                                             button=f'{language}_button')
    for i in range(1, count + 1):
        banner_arg = random.choice(banner_args)
        banner = Banner.objects.create(
            bigimage='default-banner-bigimage.png',
            smallimage='default-banner-smallimage.png',
            link='http://ezgo-buy.com/',
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
    def loop_categoreis(data, main_category=None):
        for cate in data:
            obj = dict()
            if main_category:
                obj['main_category'] = main_category
            # simple loop
            if isinstance(cate, str):
                obj['name'] = cate
                instance = Category.objects.create(**obj)
                continue

            for key in ['name', 'image_url']:
                if cate.get(key):
                    obj[key] = cate[key]

            instance = Category.objects.create(**obj)
            if cate.get('children'):
                loop_categoreis(cate['children'], instance)

    loop_categoreis(categories)


def generate_tags():
    tag_image_1 = TagImage.objects.create(name='一般-綠', image_url='label-green')
    tag_image_2 = TagImage.objects.create(name='一般-橘', image_url='label-yellow')
    tag_image_3 = TagImage.objects.create(name='一般-粉', image_url='label-pink')
    tag_image_4 = TagImage.objects.create(name='緞帶-橘', image_url='ribbon-orange')
    tag_image_5 = TagImage.objects.create(name='緞帶-綠', image_url='ribbon-green')
    tag_image_6 = TagImage.objects.create(name='緞帶-黃', image_url='ribbon-yellow')
    tag_image_7 = TagImage.objects.create(name='緞帶-粉', image_url='ribbon-pink')
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


def generate_products_for_test(count, config_data):
    spec_level1 = ['S', 'SM', 'M', 'L', 'XL', 'XX']
    spec_level2 = ['紅色', '藍色', '黃色', '綠色', '白色', '黑色']
    tag = Tag.objects.all()
    brand = Brand.objects.all()
    category = Category.objects.all()
    now = timezone.now().strftime('%Y%m%d')
    for i in range(count):
        # config data
        number_count = random.choice(range(5, 10))
        weight = 0.6 if config_data.weight else None
        price = random.randint(100, 1000)
        fake_price = 213
        inventory_status = 0 if config_data.product_stock_setting != 2 else random.randint(1, 3)
        quantity = None if config_data.product_stock_setting != 3 else random.randint(0, 10)
        # ----

        dct = dict(
            product_number=f'P{now}{i}',
            brand=random.choice(brand),
            name=f'黑人頭內褲{i}',
            title='title',
            sub_title='sub_title',
            product_info="""<div class="red">包貨時本公司可能會需要將外盒拆除，以方便運送，產品品質將不受影響。產品運送時可能因機上艙壓而造成產品渗漏，由於這點本公司無法控制，因此無法做任何賠償，敬請見諒。</div><div class="red">訂購超過 12 瓶的買家，請分開下單，並提供多個收件人資料，本公司會協助將包裹分開寄出。</div><p>產品簡介</p><p>美國好市多 Costco 獨家銷售的 KirkLand 5% Minoxidil 生髮水所含的成份與落健 5% 強效生髮水相同，對於經常使用且不想花大錢的人來說是個不錯的選擇。</p><li>無色無味</li><li>每罐容量 ： 60ml</li><li>含有 5% 的 Minoxidil</li><li>實驗證明能幫助頭髮重新生長</li><li>有效刺激毛囊，幫助毛囊再度生長</li><li>通常在 2 ~ 4 個月就可以看到成效</li><li>價格比同效果的落健更為划算</li><li>此產品為男性專用，女性不可使用</li><p>&nbsp;</p><p>Kirkland 生髮水的有效成分為 5% 的 Minoxidil ( 米諾地爾 )，Minoxidil 是目前唯一被美國 FDA 認證有效的外用生髮產品，已有充分的臨床試驗證實米諾地爾對雄激素性脫髮（ 遺傳型脫髮、脂溢型脫髮 ），斑禿等都有較好的療效。</p><em><i>*這些聲明尚未經過美國食品和藥物管理局評估。本產品不能用於診斷，治療，治癒或預防任何疾病。</i></em><p>&nbsp;</p><figure class="table"><table><tbody><tr><td colspan="2">&nbsp;<strong>產品規格</strong>&nbsp;</td></tr><tr><td>製造廠商</td><td>&nbsp;Costco Wholesale Corporation</td></tr><tr><td>&nbsp;製造產地</td><td>以色列&nbsp;</td></tr><tr><td>保存期限&nbsp;</td><td>新貨 保存期限到 2021 年 1 月&nbsp;</td></tr><tr><td>產品容量&nbsp;</td><td>6 瓶 x 60 ml - ( 共六個月份量 &nbsp;)</td></tr><tr><td>產品重量&nbsp;</td><td>1.3 磅&nbsp;</td></tr><tr><td>產品體積&nbsp;</td><td>原廠包裝 ( 英寸 ) : 6 x 5.5 x 3&nbsp;</td></tr></tbody></table></figure>""",
            detail_info="""<p><strong>使用方式 :</strong></p><li>每天在脫髮區域用滴液管滴兩次，每次 1 mL</li><li>使用更多劑量或更多次數不會有任何幫助</li><li>持續使用才能確保頭髮持續再生，不然脫髮會再次出現</li><figure class="table"><table><tbody><tr><td colspan="2"><strong>Drug Facts ( 藥物成份表 )</strong></td></tr><tr><td colspan="2"><strong>Active Ingredient ( 活性成分 )</strong></td></tr><tr><td>Minoxidil 5% w/v ( 米諾地爾 )</td><td>Hair regrowth treatment for men ( 男性頭髮再生治療 )</td></tr><tr><td colspan="2"><strong>USE</strong> to regrow hair on the top of the scalp ( vertex only )<br>效用 : 幫助頂部頭髮再生（ 僅適用於髮渦性禿頭）</td></tr><tr><td colspan="2"><strong>Warnings ( 警告 )</strong><br><strong>For external use only, For use by men only</strong><br><strong>( 僅供外部使用，僅供男性使用 )</strong><br><strong>Flammable:</strong> keep away from fire or flame<br><strong>( 易燃：遠離火源或火焰 )</strong></td></tr><tr><td colspan="2"><p><strong>Do not use if ( 如有以下狀況請停止使用 )</strong></p><li>you are woman ( 你是女姓 )</li><li>your amount of hair loss is different than that shown on the side of this carton or your hair loss is on the front of the scalp. Minoxidil topical solution 5 % is not intended for frontal balness or receding hairline. ( 你的脫髮量與這個紙核側面圖案上顯示的不同，或者你的脫髮是在前面部位。 米諾地爾不適用於前禿或退後髮線。 )</li><li>you have no family history of hair loss ( 家族裡沒有其他成員有落髮現象出現 )</li><li>your hair loss is sudden and/or patchy ( 你的脫髮是突然發生 和/或 出現片狀落髮 )</li><li>you do not know the reason for your hair loss ( 你不知道落髮原因 )</li><li>you are under 18 years of age. do not use on babies and children ( 未滿 18歲，不可使用於嬰兒或兒童 )</li><li>your scalp is red, inflamed, infected, irritated, or painful ( 您的頭皮發紅、發炎、感染、刺痛 或疼痛感 )</li><li>you use other medicines on the scalp ( 頭皮上使用其他藥物 )</li></td></tr><tr><td colspan="2"><strong>Ask a doctor before use if you have heart disease</strong><br><strong>( 如果您患有心髒病，請在使用前詢問醫生 )</strong></td></tr><tr><td colspan="2"><p><strong>When using this product ( 使用這項產品時 )</strong></p><li>do not apply on other parts of the body ( 請勿使用在其他身體部位 )</li><li>avoid contact with the eyes. In case of accidental contact, rinse eyes with large amounts of cool tap water. ( 請避免接觸眼睛。 萬一意外接觸，請量盡快使用大量冷水沖洗眼睛。 )</li><li>some people have experienced changes in hair color and/or texture ( 部份使用者出現髮色和髮質的變化 )</li><li>it takes time to regrow hair. Results may occur at 2 months with twice a day usage. For some men, you may need to use this product at least 4 months before you see results. ( 生髮需要時間。每日使用兩次的使用者通常需要2個月的時間才會看到成效。而部份男士可能需要至少4個月才能看到效果。 )</li><li>the amount of hair regrowth is different for each person. This product will not work for all men ( 每人頭髮再生的情況不同。本產品不適合所有男士使用 )</li></td></tr><tr><td colspan="2"><p><strong>Stop use and ask a doctor if ( 發生以下情況請停止使用並詢問專業醫師 )</strong></p><li>chest pain, rapid heartbeat, fantness, or dizziness occurs ( 胸痛，心跳加快，暈厥或眩暈 )</li><li>sudden, unexplained weight gain occurs ( 突然發生、不明原因的體重增加 )</li><li>your hands or feet swell ( 你的手或腳腫脹 )</li><li>scalp irritation or redness occurs ( 發生頭皮刺痛或發紅 )</li><li>unwanted facial hair growth occurs ( 出現不需要的毛髮生長 )</li><li>you do not see hair regrowth in 4 month ( 4 個月內看不到頭髮再度生長 )</li></td></tr><tr><td colspan="2"><strong>May be harmful if used when pregnant or breast-feeding. ( 懷孕或哺乳時使用可能有害 )</strong><br><strong>keep out of reach of children.</strong>if swallowed, get medical help or contact a Poison Control center right away (<strong> 遠離兒童</strong>。如果吞嚥，請馬上尋求醫療幫助 )</td></tr><tr><td colspan="2"><p><strong>Directions ( 使用方式 )</strong></p><li>apply one mL with dropper 2 times a day directly onto the scalp in the hair loss area ( 每天在脫髮區域用滴液管滴兩次，每次 1 mL)</li><li>using more or more often will not improve result ( 使用更多劑量或更多次數不會有任何幫助 )</li><li>continued use is necessary to increase and keep your hair regrowth, or hair loss will begin again ( 持續使用才能確保頭髮持續再生，不然脫髮會再次出現 )</li></td></tr><tr><td colspan="2"><p><strong>Other informantion ( 其他資料 )</strong></p><li>see hair loss pictures on the side of this carton ( 請看紙盒側面的脫髮圖片 )</li><li>before use, read all information on carton and enclosed leaflet ( 使用前請閱讀外盒上的資訊以及附帶的說明書 )</li><li>keep the carton. it contains important information ( 保留紙盒。 它包含了重要信息 )</li><li>hair regrowth has not been shown to last longer than 48 weeks in large clinical trials with continuous treatment with minoxidil topical solution 5 % for men ( 在大規模臨床試驗中，連續用 5% 米諾地爾治療的實驗者，頭髮再生長期沒有超過48週 )</li><li>in clinical studies with mostly white men aged 18-49 years of moderate degress of hair loss, minoxidil topical solution 5% for men provided more hair regrowth than minoxidil topical solution 2% ( 在臨床試驗中，大部份的實驗對象大多為白人，年記 18到49歲，擁有中等程度的脫髮。實驗證明 5% 的米諾地爾效果比 2% 的還要有效。 )</li><li>store at 20° to 25°C (68° to 77°F). keep tightly closed. (請保存於 20°C 至 25°C（ 68° 至 77 °F ）的溫度內，並保持蓋子密閉。 )</li></td></tr><tr><td colspan="2"><strong>Inactive ingredients ( 非活性成分 )</strong> alcohol ( 酒精 ), propylene glycol ( 丙二醇 ), purified water( 淨化水 )</td></tr></tbody></table></figure><p>&nbsp;</p>""",
        )
        product = Product.objects.create(
            **dct
        )
        if i % 2 == 0:
            product.tag.add(random.choice(tag))
        product.category.add(random.choice(category))
        product.save()
        ProductImage.objects.create(
            product=product,
            image_url='default-banner-smallimage.png',
            main_image=True,
        )
        ProductImage.objects.create(
            product=product,
            image_url='default-banner-smallimage.png',
            main_image=False,
        )
        # 規格細節
        if config_data.product_specifications_setting == 2:
            pass
        # 只有規格名稱
        elif config_data.product_specifications_setting == 1:
            spec1 = Specification.objects.create(
                product=product,
                name='一般',
            )
            SpecificationDetail(
                product=product,
                level1_spec=spec1,
                product_code=f'{generate_members(10)}',
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
    store = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='5', price=65,
        cash_on_delivery=True, frontend_name='萊爾富', backstage_name='超商取貨（萊爾富）',
        sub_type='HILIFE'
    )
    store = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='5', price=65,
        cash_on_delivery=True, frontend_name='7-11', backstage_name='超商取貨（7-11）',
        sub_type='UNIMART'
    )
    store = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='5', price=65,
        cash_on_delivery=True, frontend_name='全家', backstage_name='超商取貨（全家）',
        sub_type='FAMI'
    )
    home_delivery = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='999', price=90,
        cash_on_delivery=False, frontend_name='宅配', backstage_name='宅配'
    )
    post = FreeShipping.objects.create(
        title='全館滿 3000就免運欸!! 太划算了', role='3000', weight='1', price=60,
        cash_on_delivery=False, frontend_name='郵寄', backstage_name='郵寄'
    )


def generate_coupon(count):
    for i in range(count):
        Coupon.objects.create(
            role=random.randint(0, 100),
            method=random.choice([1, 2]),
            discount=random.randint(0, 100),
            title=f'折價券{i}',
            discount_code=f'DC{get_random_number(7)}',
            image_url='11697.jpg',
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(days=random.randint(-20, 20)),
        )


if __name__ == '__main__':
    main()
