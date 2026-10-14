from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from people.models import Helper
from people.selectors.people import helper_queryset
from people.serializers.helper import HelperReadSerializer, HelperWriteSerializer
from people.services.people import create_person, set_person_active, update_person


class HelperListCreateView(generics.ListCreateAPIView):
    search_fields = ("name", "phone", "normalized_phone", "note")
    filterset_fields = ("is_active",)
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("name",)

    def get_queryset(self):
        return helper_queryset()

    def get_serializer_class(self):
        return HelperWriteSerializer if self.request.method == "POST" else HelperReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = HelperWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        helper = create_person(
            model=Helper, data=serializer.validated_data,
            actor=request.user, request=request,
        )
        return Response(HelperReadSerializer(helper_queryset().get(pk=helper.pk)).data, status=status.HTTP_201_CREATED)


class HelperDetailView(generics.RetrieveAPIView):
    queryset = helper_queryset()
    serializer_class = HelperReadSerializer

    def patch(self, request, *args, **kwargs):
        serializer = HelperWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        helper = update_person(
            instance=self.get_object(), data=serializer.validated_data,
            actor=request.user, request=request,
        )
        return Response(HelperReadSerializer(helper_queryset().get(pk=helper.pk)).data)


class HelperActiveView(GenericAPIView):
    queryset = Helper.objects.all()
    serializer_class = HelperReadSerializer
    is_active = True

    def post(self, request, pk):
        helper = set_person_active(
            instance=self.get_object(), is_active=self.is_active,
            actor=request.user, request=request,
        )
        return Response(HelperReadSerializer(helper_queryset().get(pk=helper.pk)).data)


class HelperDeactivateView(HelperActiveView):
    is_active = False


class HelperReactivateView(HelperActiveView):
    is_active = True
