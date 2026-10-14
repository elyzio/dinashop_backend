from rest_framework import generics, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from people.models import Customer
from people.selectors.people import customer_queryset
from people.serializers.customer import CustomerReadSerializer, CustomerWriteSerializer
from people.services.people import create_person, set_person_active, update_person


class CustomerListCreateView(generics.ListCreateAPIView):
    search_fields = ("name", "phone", "normalized_phone", "address", "note")
    filterset_fields = ("is_active", "is_walk_in")
    ordering_fields = ("name", "created_at", "updated_at")
    ordering = ("name",)

    def get_queryset(self):
        return customer_queryset()

    def get_serializer_class(self):
        return CustomerWriteSerializer if self.request.method == "POST" else CustomerReadSerializer

    def create(self, request, *args, **kwargs):
        serializer = CustomerWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = create_person(
            model=Customer, data=serializer.validated_data,
            actor=request.user, request=request,
        )
        customer = customer_queryset().get(pk=customer.pk)
        return Response(CustomerReadSerializer(customer).data, status=status.HTTP_201_CREATED)


class CustomerDetailView(generics.RetrieveAPIView):
    queryset = customer_queryset()
    serializer_class = CustomerReadSerializer

    def patch(self, request, *args, **kwargs):
        serializer = CustomerWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        customer = update_person(
            instance=self.get_object(), data=serializer.validated_data,
            actor=request.user, request=request,
        )
        return Response(CustomerReadSerializer(customer_queryset().get(pk=customer.pk)).data)


class CustomerActiveView(GenericAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerReadSerializer
    is_active = True

    def post(self, request, pk):
        customer = set_person_active(
            instance=self.get_object(), is_active=self.is_active,
            actor=request.user, request=request,
        )
        return Response(CustomerReadSerializer(customer_queryset().get(pk=customer.pk)).data)


class CustomerDeactivateView(CustomerActiveView):
    is_active = False


class CustomerReactivateView(CustomerActiveView):
    is_active = True
