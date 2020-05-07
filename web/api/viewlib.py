from django.shortcuts import get_object_or_404
from rest_framework.response import Response


class List2RetrieveMixin:
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        instance = get_object_or_404(queryset)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class NestedViewSetBase:
    # example: company
    parent_model: str = ''

    def get_queryset(self):
        parent_key = self.parent_model + '_pk'
        filter_kwargs = {
            f'{self.parent_model}_id': self.kwargs[parent_key]
        }
        return self.queryset.filter(**filter_kwargs)
