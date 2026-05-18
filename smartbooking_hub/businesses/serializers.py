from rest_framework import serializers
from .models import Business, UserBusiness, Service, BusinessHour

class BusinessHourSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessHour
        fields = '__all__'

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'

class BusinessSerializer(serializers.ModelSerializer):
    hours = BusinessHourSerializer(many=True, read_only=True)
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Business
        fields = ['id', 'name', 'slug', 'phone', 'email', 'address', 'plan_type', 'is_active', 'hours', 'services', 'created_at']

class UserBusinessSerializer(serializers.ModelSerializer):
    business_name = serializers.ReadOnlyField(source='business.name')
    user_email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = UserBusiness
        fields = ['id', 'user', 'user_email', 'business', 'business_name', 'business_role', 'created_at']