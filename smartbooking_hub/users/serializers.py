from rest_framework import serializers
from .models import User, Client

class UserSerializer(serializers.ModelSerializer):
    # Campo de contraseña de solo escritura para máxima seguridad
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'password', 'role', 'is_active', 'created_at']
        read_only_fields = ['created_at', 'is_active']

    def create(self, validated_data):
        # Extraemos la contraseña antes de guardar
        password = validated_data.pop('password')
        
        # Usamos la creación segura de Django para encriptar la clave
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        return user

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'