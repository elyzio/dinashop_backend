from rest_framework import serializers

from people.models import Helper, normalize_phone


class HelperReadSerializer(serializers.ModelSerializer):
    completed_jobs = serializers.SerializerMethodField()
    fees_cents = serializers.SerializerMethodField()
    cod_collected_cents = serializers.SerializerMethodField()
    cod_handed_over_cents = serializers.SerializerMethodField()
    cod_held_cents = serializers.SerializerMethodField()

    class Meta:
        model = Helper
        fields = (
            "id", "name", "phone", "normalized_phone", "note", "is_active",
            "completed_jobs", "fees_cents", "cod_collected_cents",
            "cod_handed_over_cents", "cod_held_cents", "created_at", "updated_at",
        )
        read_only_fields = fields

    def get_completed_jobs(self, obj) -> int:
        return sum(job.status == job.Status.DELIVERED for job in obj.delivery_jobs.all())

    def get_fees_cents(self, obj) -> int:
        return sum(job.fee_cents for job in obj.delivery_jobs.all())

    def get_cod_collected_cents(self, obj) -> int:
        return sum(job.cod_payment.amount_cents for job in obj.delivery_jobs.all() if job.cod_payment_id)

    def get_cod_handed_over_cents(self, obj) -> int:
        return sum(item.amount_cents for item in obj.cod_handovers.all())

    def get_cod_held_cents(self, obj) -> int:
        return max(0, self.get_cod_collected_cents(obj) - self.get_cod_handed_over_cents(obj))


class HelperWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    phone = serializers.CharField(max_length=40, allow_blank=True, required=False)
    note = serializers.CharField(allow_blank=True, required=False)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value

    def validate_phone(self, value):
        value = value.strip()
        if value and not normalize_phone(value).lstrip("+").isdigit():
            raise serializers.ValidationError("Enter a valid phone number.")
        return value
