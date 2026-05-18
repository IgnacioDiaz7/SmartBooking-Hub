from rest_framework import serializers
from .models import TimeBlock, Booking, BookingStatusHistory

class TimeBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeBlock
        fields = '__all__'

class BookingStatusHistorySerializer(serializers.ModelSerializer):
    changed_by_email = serializers.ReadOnlyField(source='changed_by_user.email')

    class Meta:
        model = BookingStatusHistory
        fields = ['id', 'booking', 'old_status', 'new_status', 'changed_by_user', 'changed_by_email', 'reason', 'changed_at']

class BookingSerializer(serializers.ModelSerializer):
    # Añadimos detalles extra en modo lectura para facilitar la vista en React
    client_name = serializers.ReadOnlyField(source='client.first_name')
    worker_name = serializers.ReadOnlyField(source='worker.first_name')
    service_name = serializers.ReadOnlyField(source='service.name')

    class Meta:
        model = Booking
        fields = [
            'id', 'business', 'client', 'client_name', 'worker', 'worker_name', 
            'service', 'service_name', 'booking_date', 'start_time', 'end_time', 
            'status', 'notes', 'source', 'total_price', 'created_at'
        ]