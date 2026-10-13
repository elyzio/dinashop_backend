from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView

from users.models import NotificationReceipt
from users.selectors.notification_receipt import notification_receipt_queryset
from users.serializers.notification_receipt import (
    NotificationAcknowledgeSerializer,
    NotificationReadAllSerializer,
    NotificationReceiptSerializer,
)
from users.services.notification_receipt import (
    acknowledge_notification,
    mark_notifications_read,
)


class NotificationReceiptListView(generics.ListAPIView):
    serializer_class = NotificationReceiptSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ("notification_id", "fingerprint", "read_at", "dismissed_at")
    ordering_fields = ("created_at", "updated_at", "read_at", "dismissed_at")
    ordering = ("-updated_at",)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return NotificationReceipt.objects.none()
        return notification_receipt_queryset(user=self.request.user)


class NotificationAcknowledgeView(GenericAPIView):
    serializer_class = NotificationAcknowledgeSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = NotificationAcknowledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receipt = acknowledge_notification(
            user=request.user,
            **serializer.validated_data,
        )
        return Response(NotificationReceiptSerializer(receipt).data)


class NotificationReadAllView(GenericAPIView):
    serializer_class = NotificationReadAllSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = NotificationReadAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receipts = mark_notifications_read(
            user=request.user,
            items=serializer.validated_data["items"],
        )
        return Response(
            NotificationReceiptSerializer(receipts, many=True).data,
            status=status.HTTP_200_OK,
        )
