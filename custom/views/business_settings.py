from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from custom.models import BusinessSettings
from custom.serializers.business_settings import BusinessSettingsSerializer
from custom.services.business_settings import save_business_settings


class BusinessSettingsCurrentView(GenericAPIView):
    serializer_class = BusinessSettingsSerializer
    def get(self, request):
        instance = get_object_or_404(BusinessSettings, key="default")
        return Response(BusinessSettingsSerializer(instance).data)

    def put(self, request):
        instance = BusinessSettings.objects.filter(key="default").first()
        serializer = BusinessSettingsSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        result = save_business_settings(serializer=serializer, actor=request.user, request=request)
        return Response(
            BusinessSettingsSerializer(result).data,
            status=status.HTTP_200_OK if instance else status.HTTP_201_CREATED,
        )

    def patch(self, request):
        instance = get_object_or_404(BusinessSettings, key="default")
        serializer = BusinessSettingsSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        result = save_business_settings(serializer=serializer, actor=request.user, request=request)
        return Response(BusinessSettingsSerializer(result).data)
