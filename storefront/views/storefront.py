from django.shortcuts import get_object_or_404
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from custom.models import BusinessSettings
from storefront.serializers.storefront import PublicStorefrontSerializer

from .base import PublicStorefrontViewMixin


class PublicStorefrontView(PublicStorefrontViewMixin, GenericAPIView):
    serializer_class = PublicStorefrontSerializer

    def get(self, request):
        settings = get_object_or_404(BusinessSettings, key="default")
        return Response(self.get_serializer(settings).data)
