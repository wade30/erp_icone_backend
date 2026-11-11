from rest_framework import serializers

from .models import Entrepreneur, Project, CoachingSession


class EntrepreneurSerializer(serializers.ModelSerializer):

    class Meta:
        model = Entrepreneur
        fields = "__all__"


class ProjectSerializer(serializers.ModelSerializer):

    entrepreneur_name = serializers.CharField(
        source="entrepreneur.__str__",
        read_only=True
    )

    class Meta:
        model = Project
        fields = "__all__"


class CoachingSessionSerializer(serializers.ModelSerializer):

    coach_name = serializers.StringRelatedField(
        source="coach",
        read_only=True
    )

    class Meta:
        model = CoachingSession
        fields = "__all__"