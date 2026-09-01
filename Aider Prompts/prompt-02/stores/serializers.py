import bleach
from rest_framework import serializers
from .models import Store

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = '__all__'
        read_only_fields = ('id','owner','created_at','is_active')
    def validate_description(self, v): return bleach.clean(v or '', strip=True)
    def validate_return_policy(self, v): return bleach.clean(v or '', strip=True)
