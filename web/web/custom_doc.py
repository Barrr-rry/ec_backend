from rest_framework.renderers import DocumentationRenderer
from django.template import loader


class MyDocumentationRenderer(DocumentationRenderer):
    template = 'custom_docs/index.html'


api_doc_header = {}


def update_schema(schema):
    # todo 之後要加入回來
    # for key in api_doc_header:
    #     for before, after in api_doc_header[key]:
    #         if len(before.split('>')) == 1:
    #             if before not in schema._data[key]._data:
    #                 continue
    #             schema._data[key]._data[after] = schema._data[key]._data[before]
    #             del schema._data[key]._data[before]
    #         elif len(before.split('>')) == 2:
    #             before_1, before_2 = before.split('>')
    #             if (before_1 not in schema._data[key]._data
    #                     or before_2 not in schema._data[key]._data[before_1]):
    #                 continue
    #             schema._data[key]._data[after] = schema._data[key]._data[before_1]._data[before_2]
    #             del schema._data[key]._data[before_1]._data[before_2]
    #         elif len(before.split('>')) == 3:
    #             before_1, before_2, before_3 = before.split('>')
    #             if (before_1 not in schema._data[key]._data
    #                     or before_2 not in schema._data[key]._data[before_1]
    #                     or beofre_3 not in schema._data[key]._data[before_1]._data[before_2]):
    #                 continue
    #             schema._data[key]._data[after] = schema._data[key]._data[before_1]._data[before_2]._data[before_3]
    #             del schema._data[key]._data[before_1]._data[before_2]._data[before_3]
    return schema
