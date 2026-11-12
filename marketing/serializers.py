from rest_framework import serializers

from .models import Client, Contract, ServiceOrder


class ClientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Client
        fields = "__all__"


class ContractSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contract
        fields = "__all__"


class ServiceOrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = ServiceOrder
        fields = "__all__"