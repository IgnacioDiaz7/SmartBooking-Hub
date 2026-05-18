from rest_framework import serializers
from .models import Worker, WorkerService, WorkerAvailability

class WorkerAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkerAvailability
        fields = '__all__'

class WorkerServiceSerializer(serializers.ModelSerializer):
    # Traemos el nombre del servicio para que el frontend lo muestre fácilmente
    service_name = serializers.ReadOnlyField(source='service.name')

    class Meta:
        model = WorkerService
        fields = ['id', 'worker', 'service', 'service_name', 'created_at']

class WorkerSerializer(serializers.ModelSerializer):
    availabilities = WorkerAvailabilitySerializer(many=True, read_only=True)
    services = serializers.SerializerMethodField()

    class Meta:
        model = Worker
        fields = ['id', 'business', 'user', 'first_name', 'last_name', 'phone', 'email', 'specialty', 'is_active', 'services', 'availabilities', 'created_at']

    def get_services(self, obj):
        # Devuelve solo los servicios activos asociados a este trabajador
        worker_services = WorkerService.objects.filter(worker=obj)
        return WorkerServiceSerializer(worker_services, many=True).data