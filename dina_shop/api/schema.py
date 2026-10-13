from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    fields = serializers.DictField(
        child=serializers.ListField(child=serializers.CharField()),
        required=False,
    )


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorDetailSerializer()
