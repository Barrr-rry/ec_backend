"""
複製rest_framework/documentation 以及 rest_framework/schemas 以及 schemas/view
"""
from django.conf.urls import include, url

from rest_framework.renderers import (
    CoreJSONRenderer, SchemaJSRenderer
)
from rest_framework.schemas import SchemaGenerator
from rest_framework.settings import api_settings

from rest_framework.settings import api_settings

from rest_framework.schemas import coreapi, openapi
from rest_framework.schemas.inspectors import DefaultSchema  # noqa
from rest_framework.schemas.coreapi import AutoSchema, ManualSchema, SchemaGenerator  # noqa

"""
views.py        # Houses `SchemaView`, `APIView` subclass.

See schemas.__init__.py for package overview.
"""
from rest_framework import exceptions, renderers
from rest_framework.response import Response
from rest_framework.schemas import coreapi
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from rest_framework.schemas.views import SchemaView
from . import custom_doc


class MySchemaView(SchemaView):

    def get(self, request, *args, **kwargs):
        schema = self.schema_generator.get_schema(request, self.public)
        if schema is None:
            raise exceptions.PermissionDenied()
        # 主要要改的地方
        schema = custom_doc.update_schema(schema)
        return Response(schema)


def get_schema_view(
        title=None, url=None, description=None, urlconf=None, renderer_classes=None,
        public=False, patterns=None, generator_class=None,
        authentication_classes=api_settings.DEFAULT_AUTHENTICATION_CLASSES,
        permission_classes=api_settings.DEFAULT_PERMISSION_CLASSES,
        version=None):
    """
    Return a schema view.
    """
    if generator_class is None:
        if coreapi.is_enabled():
            generator_class = coreapi.SchemaGenerator
        else:
            generator_class = openapi.SchemaGenerator

    generator = generator_class(
        title=title, url=url, description=description,
        urlconf=urlconf, patterns=patterns, version=version
    )
    # 主要要改的地方
    return MySchemaView.as_view(
        renderer_classes=renderer_classes,
        schema_generator=generator,
        public=public,
        authentication_classes=authentication_classes,
        permission_classes=permission_classes,
    )


def get_docs_view(
        title=None, description=None, schema_url=None, urlconf=None,
        public=True, patterns=None, generator_class=SchemaGenerator,
        authentication_classes=api_settings.DEFAULT_AUTHENTICATION_CLASSES,
        permission_classes=api_settings.DEFAULT_PERMISSION_CLASSES,
        renderer_classes=None):
    if renderer_classes is None:
        # 改變的地方
        renderer_classes = [custom_doc.MyDocumentationRenderer, CoreJSONRenderer]

    return get_schema_view(
        title=title,
        url=schema_url,
        urlconf=urlconf,
        description=description,
        renderer_classes=renderer_classes,
        public=public,
        patterns=patterns,
        generator_class=generator_class,
        authentication_classes=authentication_classes,
        permission_classes=permission_classes,
    )


def get_schemajs_view(
        title=None, description=None, schema_url=None, urlconf=None,
        public=True, patterns=None, generator_class=SchemaGenerator,
        authentication_classes=api_settings.DEFAULT_AUTHENTICATION_CLASSES,
        permission_classes=api_settings.DEFAULT_PERMISSION_CLASSES):
    renderer_classes = [SchemaJSRenderer]

    return get_schema_view(
        title=title,
        url=schema_url,
        urlconf=urlconf,
        description=description,
        renderer_classes=renderer_classes,
        public=public,
        patterns=patterns,
        generator_class=generator_class,
        authentication_classes=authentication_classes,
        permission_classes=permission_classes,
    )


def include_docs_urls(
        title=None, description=None, schema_url=None, urlconf=None,
        public=True, patterns=None, generator_class=SchemaGenerator,
        authentication_classes=api_settings.DEFAULT_AUTHENTICATION_CLASSES,
        permission_classes=[],
        renderer_classes=None):
    docs_view = get_docs_view(
        title=title,
        description=description,
        schema_url=schema_url,
        urlconf=urlconf,
        public=public,
        patterns=patterns,
        generator_class=generator_class,
        authentication_classes=authentication_classes,
        renderer_classes=renderer_classes,
        permission_classes=permission_classes,
    )
    schema_js_view = get_schemajs_view(
        title=title,
        description=description,
        schema_url=schema_url,
        urlconf=urlconf,
        public=public,
        patterns=patterns,
        generator_class=generator_class,
        authentication_classes=authentication_classes,
        permission_classes=permission_classes,
    )
    urls = [
        url(r'^$', docs_view, name='docs-index'),
        url(r'^schema.js$', schema_js_view, name='schema-js')
    ]
    return include((urls, 'api-docs'), namespace='api-docs')
