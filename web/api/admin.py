from django.contrib import admin
from .models import (BannerContent, Banner, File, Permission, Manager, AdminTokens, Member, Brand, Product,
                     Specification, MemberTokens, Order, MemberStore, Reward, RewardRecord, MemberAddress,
                     ProductImage, Category, Tag, TagImage, Cart, ProductQuitShot, FreeShipping, Coupon,
                     MemberWish, ConfigSetting, SpecificationDetail, Country, RewardRecordTemp
                     )
from django.db.models.fields.related import ForeignKey, ManyToManyField
from django.db.models.fields.reverse_related import ManyToOneRel, ManyToManyRel

modellist = (BannerContent, Banner, File, Permission, Manager, AdminTokens, Member, Brand, Product,
             Specification, MemberTokens, Order, MemberStore, Reward, RewardRecord, MemberAddress,
             ProductImage, Category, Tag, TagImage, Cart, ProductQuitShot, FreeShipping, Coupon,
             MemberWish, ConfigSetting, SpecificationDetail, Country, RewardRecordTemp
             )

# 後台管理需要設定要監控哪些model
for md in modellist:
    """
    admin 監控的寫法
    這邊寫成這樣是不要每一個model 都還要產生新的class 
    自己寫一個for loop 自動產生新的class 減少重複工
    """
    list_display = []
    # 關聯資料的部分不好顯示則沒有顯示
    for field in md._meta.get_fields():
        if isinstance(field, ForeignKey):
            list_display.append(field.attname)
        elif isinstance(field, ManyToOneRel):
            pass
        elif isinstance(field, ManyToManyRel) or isinstance(field, ManyToManyField):
            pass
        else:
            list_display.append(field.name)
    datetime_list = []
    # 基本資料 這個可以不用新增
    for i in ['created_at', 'updated_at', 'deleted_at', 'created']:
        if i in list_display:
            list_display.remove(i)
            datetime_list.append(i)
    list_display += datetime_list

    # 動態init 一個 class 並且註冊他
    class_name = f'{md.__name__}Admin'
    cls = type(class_name, (admin.ModelAdmin,), dict(
        list_display=list_display,
    ))
    # 註冊一個class 上面的工程是自動建立一個class
    admin.site.register(md, cls)
