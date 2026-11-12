from rest_framework import serializers

from .models import Course, Learner, Enrollment


class CourseSerializer(serializers.ModelSerializer):

    class Meta:
        model = Course
        fields = "__all__"


class LearnerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Learner
        fields = "__all__"


class EnrollmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Enrollment
        fields = "__all__"

        read_only_fields = ["id"]

    def validate(self, attrs):
        amount_due = attrs.get(
            "amount_due",
            getattr(self.instance, "amount_due", 0)
        )

        amount_paid = attrs.get(
            "amount_paid",
            getattr(self.instance, "amount_paid", 0)
        )

        if amount_due < 0 or amount_paid < 0:
            raise serializers.ValidationError(
                "Les montants ne peuvent pas être négatifs."
            )

        if amount_paid > amount_due:
            raise serializers.ValidationError(
                "Le montant payé dépasse le montant dû."
            )

        return attrs