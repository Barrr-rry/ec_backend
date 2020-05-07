from rest_framework.authentication import TokenAuthentication as BaseTokenAuthentication
from rest_framework.authentication import get_authorization_header, exceptions
# todo 之後要加入回來
from .models import AdminTokens, MemberTokens
from django.contrib.auth.models import AnonymousUser


class AnnoymousAuthentication(BaseTokenAuthentication):
    model = None

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        return super().authenticate(request)

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.get(key=key)
            if token.expired():
                token.delete()
                raise exceptions.AuthenticationFailed('Auth expire time error')
            return token.user, token
        except Exception as e:
            return AnonymousUser(), None


class NeedTokenAuthentication(BaseTokenAuthentication):
    model = None

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth:
            raise exceptions.AuthenticationFailed
        return super().authenticate(request)

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')
        if token.expired():
            token.delete()
            raise exceptions.AuthenticationFailed('Auth expire time error')

        return token.user, token


class TokenAuthentication(NeedTokenAuthentication):
    model = AdminTokens


class TokenCheckAuthentication(AnnoymousAuthentication):
    model = AdminTokens


class MemberAuthentication(NeedTokenAuthentication):
    model = MemberTokens


class MemberCheckAuthentication(AnnoymousAuthentication):
    model = MemberTokens


class MangerOrMemberAuthentication(AnnoymousAuthentication):
    model = AdminTokens

    def get_token(self, queryset):
        if not queryset.count():
            return None
        token = queryset.first()
        if not token.user.is_active:
            return None
        if token.expired():
            token.delete()
            return None
        return token

    def authenticate_credentials(self, key):
        admintokenqueryset = AdminTokens.objects.filter(key=key)
        membertokenqueryset = MemberTokens.objects.filter(key=key)
        token = self.get_token(admintokenqueryset)
        if not token:
            token = self.get_token(membertokenqueryset)
        if not token:
            return AnonymousUser(), None
        else:
            return token.user, token
