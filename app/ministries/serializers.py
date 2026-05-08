from rest_framework import serializers
from .models import Ministry


class MinistrySerializer(serializers.ModelSerializer):

    leaderName = serializers.CharField(source='leaderAssigned.username',read_only=True)

    class Meta:
        model = Ministry

        fields = ['id','name','description','leaderAssigned','leaderName','isActive','createdAt']

    def validate_name(self, value):

        query = Ministry.objects.filter(name=value)

        if self.instance:
            query = query.exclude(id=self.instance.id)

        if query.exists():
            raise serializers.ValidationError("Ya existe un ministerio con este nombre")

        return value