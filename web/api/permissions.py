from rest_framework.permissions import BasePermission
from functools import partial
from rest_framework.authentication import TokenAuthentication as BaseTokenAuthentication
from rest_framework.authentication import get_authorization_header, exceptions
from .models import AdminTokens, Manager, Permission, Category, Tag, Brand, Member, Order
from django.contrib.auth.models import AnonymousUser


class DefaultIsAuthenticated(BasePermission):

    def has_permission(self, request, view):
        if view.action in ['retrieve', 'list']:
            return True
        user = request.user
        token = request.auth
        if (isinstance(user, Manager) or isinstance(user, Member)) and token and not token.expired():
            return True
        else:
            return False


class IsHightestPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.permission.highest_permission


class OrderOwnaerPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if view.action in ['create']:
            return True
        instance = Order.objects.get(pk=view.kwargs['pk'])
        return instance.member == user


def factory_permission(target_method_list=None, field=None, validate_values=None):
    if target_method_list is None:
        target_method_list = []
    if validate_values is None:
        validate_values = []

    class DefaultFactoryPermission(BasePermission):
        def has_permission(self, request, view):
            user = request.user
            if not hasattr(user, 'permission'):
                return False
            if view.action in target_method_list:
                target_value = getattr(user.permission, field)
                return target_value in validate_values
            return True

    return DefaultFactoryPermission


RoleManagerReadPermission = factory_permission(
    target_method_list=['list', 'retrieve'],
    field='role_manage',
    validate_values=[1, 2]
)
RoleManagerEditPermission = factory_permission(
    target_method_list=['update', 'create', 'destroy'],
    field='role_manage',
    validate_values=[2]
)
MemberManagerReadPermission = factory_permission(
    target_method_list=['list', 'retrieve'],
    field='member_manage',
    validate_values=[1, 2]
)
MemberManagerEditPermission = factory_permission(
    target_method_list=['update', 'create', 'destroy'],
    field='member_manage',
    validate_values=[2]
)
ProductManagerEditPermission = factory_permission(
    target_method_list=['update', 'create', 'destroy'],
    field='product_manage',
    validate_values=[2]
)
TagManagerEditPermission = factory_permission(
    target_method_list=['update', 'create', 'destroy'],
    field='catalog_manage',
    validate_values=[2]
)
CouponManagerEditPermission = factory_permission(
    target_method_list=['update', 'create', 'destroy'],
    field='coupon_manage',
    validate_values=[2]
)
BannerManagerEditPermission = factory_permission(
    target_method_list=['update', 'create', 'destroy'],
    field='banner_manage',
    validate_values=[2]
)
BrandManagerEditPermission = factory_permission(
    target_method_list=['update', 'create', 'destroy'],
    field='catalog_manage',
    validate_values=[2]
)
CategoryManagerEditPermission = factory_permission(
    target_method_list=['update', 'create', 'destroy'],
    field='catalog_manage',
    validate_values=[2]
)
RewardManagerEditPermission = factory_permission(
    target_method_list=['update', 'create', 'destroy'],
    field='coupon_manage',
    validate_values=[2]
)
OrderManagerEditPermission = factory_permission(
    target_method_list=['update', 'create', 'destroy'],
    field='order_manage',
    validate_values=[2]
)
OrderManagerReadPermission = factory_permission(
    target_method_list=['list', 'retrieve'],
    field='order_manage',
    validate_values=[1, 2]
)


# todo 有問題之後再重構
class RoleAuthenticated(BasePermission):
    def has_permission(self, request, view):
        # 判斷action是否為read or list
        if view.action in ['retrieve', 'list']:
            user = request.user
            # 判斷user的permission權限：highest_permission=True or role_manage=1, 2可通過
            if user.permission.highest_permission is True or user.permission.role_manage == 1 or user.permission.role_manage == 2:
                return True
            else:
                return False
        else:
            user = request.user
            # 判斷user的permission權限：highest_permission=True or role_manage=2可通過
            if user.permission.highest_permission is True or user.permission.role_manage == 2:
                # delete以外的action可通過
                if view.action != 'destroy':
                    return True
                instance = Permission.objects.get(pk=view.kwargs.get('pk'))
                # 判斷刪除權限的是否highest_permission=True or 擁有manager
                if instance.highest_permission or instance.manager.count():
                    return False
                return True

            else:
                return False


# todo 有問題之後再重構
class ManagerAuthenticated(BasePermission):

    def has_permission(self, request, view):
        # 判斷action是否為read or list
        if view.action in ['retrieve', 'list']:
            user = request.user
            # 判斷user的permission權限：highest_permission=True or role_manage=1, 2可通過
            if user.permission.highest_permission is True or user.permission.role_manage == 1 or user.permission.role_manage == 2:
                return True
            else:
                return False
        else:
            user = request.user
            # 判斷user的permission權限：highest_permission=True or role_manage=2可通過
            if user.permission.highest_permission is True or user.permission.role_manage == 2:
                # delete以外的action可通過
                if view.action not in ['update', 'destroy']:
                    return True
                instance = Manager.objects.get(pk=view.kwargs.get('pk'))
                # 判斷刪除manager的權限是否highest_permission=True
                if instance.permission.highest_permission and user.permission.highest_permission is False:
                    return False
                return True

            else:
                return False


# todo 有問題之後再重構
class CategoryAuthenticated(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        token = request.auth
        if view.action in ['retrieve', 'list']:
            return not (isinstance(user, Manager) and user.permission.coupon_manage == 0)
        if isinstance(user, Manager) and token and not token.expired():
            if view.action in ['create', 'update', 'destroy']:
                user = request.user
                if user.permission.highest_permission is True or user.permission.catalog_manage == 2:
                    if view.action != 'destroy':
                        return True
                    instance = Category.objects.get(pk=view.kwargs.get('pk'))
                    if instance.sub_categories.count() or instance.product.count():
                        return False
                    return True
                else:
                    return False
        else:
            return False


# todo 有問題之後再重構
class TagAuthenticated(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        token = request.auth
        if view.action in ['retrieve', 'list']:
            return not (isinstance(user, Manager) and user.permission.coupon_manage == 0)
        if isinstance(user, Manager) and token and not token.expired():
            if view.action in ['create', 'update', 'destroy']:
                user = request.user
                if user.permission.highest_permission is True or user.permission.catalog_manage == 2:
                    if view.action != 'destroy':
                        return True
                    instance = Tag.objects.get(pk=view.kwargs.get('pk'))
                    if instance.product.count():
                        return False
                    return True
                else:
                    return False
        else:
            return False

    # def has_permission(self, request, view):
    #     instance = Tag.objects.get(pk=view.kwargs.get('pk'))
    #     if view.action in ['destroy'] and instance.products.count():
    #         return False
    #     else:
    #         return True


# todo 有問題之後再重構
class BrandAuthenticated(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        token = request.auth
        if view.action in ['retrieve', 'list']:
            return not (isinstance(user, Manager) and user.permission.coupon_manage == 0)
        if isinstance(user, Manager) and token and not token.expired():
            if view.action in ['create', 'update', 'destroy']:
                user = request.user
                if user.permission.highest_permission is True or user.permission.catalog_manage == 2:
                    if view.action != 'destroy':
                        return True
                    instance = Brand.objects.get(pk=view.kwargs.get('pk'))
                    if instance.product.count():
                        return False
                    return True
                else:
                    return False
        else:
            return False


class MemberAuthenticated(BasePermission):

    def has_permission(self, request, view):
        # 判斷action是否為read or list
        user = request.user
        # 判斷user的permission權限：highest_permission=True or role_manage=2可通過
        if isinstance(user, Member):
            return True
        else:
            if user.permission.highest_permission is True or user.permission.member_manage == 2:
                # delete以外的action可通過
                return True

            else:
                return False


class OrderAuthenticated(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        token = request.auth
        if (isinstance(user, Member) and token and not token.expired()) and view.action in ['list', 'retrieve',
                                                                                            'create', 'update']:
            return True


class RewardRecordAuthenticated(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        token = request.auth
        if (isinstance(user, Member) and token and not token.expired()) and view.action in ['list']:
            return True


class BannerReadAuthenticated(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if view.action in ['retrieve', 'list']:
            return not (isinstance(user, Manager) and user.permission.banner_manage == 0)


class ProductReadAuthenticated(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if view.action in ['retrieve', 'list']:
            return not (isinstance(user, Manager) and user.permission.product_manage == 0)


class CouponReadAuthenticated(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        if view.action in ['retrieve', 'list']:
            return not (isinstance(user, Manager) and user.permission.coupon_manage == 0)


class ReadAuthenticated(BasePermission):

    def has_permission(self, request, view):
        if view.action in ['retrieve', 'list']:
            return True


class IsAuthenticated(BasePermission):

    def has_permission(self, request, view):
        user = request.user
        token = request.auth
        if isinstance(user, Manager) and token and not token.expired():
            return True
        else:
            return False


class PermissionDestroy(BasePermission):
    def has_permission(self, request, view):
        if view.action != 'destroy':
            return True
        instance = Permission.objects.get(pk=view.kwargs.get('pk'))
        if instance.highest_permission or instance.manager.count():
            return False
        return True
