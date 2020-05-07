"""web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from .documentation import include_docs_urls
from api.views import get_urls
from api import views
from django.conf import settings
from django.conf.urls.static import static
from api import docs

urlpatterns = [
    path('api/', include(get_urls())),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('backend/conquers/admin/', admin.site.urls),
    # path('api/ecpay/payment/', views.PaymenetViewSet.as_view()),
    # path('api/ecpay/shipping/', views.ShippingViewSet.as_view()),
    # path('api/ecpay/redirect/', views.RedirectViewSet.as_view()),
]

if settings.DEBUG:
    urlpatterns += path('docs/',
                        include_docs_urls(title='RESTFUL API', description=docs.doc_desc, authentication_classes=[])),

    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
