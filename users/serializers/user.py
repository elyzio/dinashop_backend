from rest_framework import serializers

from users.models import User


class CsrfTokenSerializer(serializers.Serializer):
    csrf_token = serializers.CharField(read_only=True)


class EmptySerializer(serializers.Serializer):
    pass


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name")
        read_only_fields = fields


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "last_name")

    def validate_first_name(self, value):
        return value.strip()

    def validate_last_name(self, value):
        return value.strip()
