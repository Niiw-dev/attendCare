from django.contrib.auth.hashers import check_password

from rest_framework import serializers

from .models import Server, ServerMinistry
from ministries.models import Ministry


class ServerSerializer(serializers.ModelSerializer):
    ministryIds = serializers.ListField(child=serializers.IntegerField(),write_only=True,
                                        required=False)
    document = serializers.CharField(required=False,allow_null=True,allow_blank=True)
    fingerprint = serializers.CharField(required=False,allow_null=True,allow_blank=True)
    ministries = serializers.SerializerMethodField()


    class Meta:

        model = Server

        fields = ['id','firstName','lastName','document','pin','fingerprint','isActive',
                  'ministries','ministryIds']

        extra_kwargs = {
            'pin': {'write_only': True},
            'fingerprint': {'write_only': True}
        }


    def get_ministries(self, obj):

        return [
            {
                'id': ministry.id,
                'name': ministry.name
            }
            for ministry in obj.ministries.all()
        ]
    

    def validate_document(self, value):

        if not value:
            return value

        queryset = Server.objects.filter(document=value)

        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
            raise serializers.ValidationError('Documento ya existe')

        return value


    def validate_pin(self, value):

        if not value.isdigit() or len(value) != 5:
            raise serializers.ValidationError('El PIN debe tener exactamente 5 dígitos')

        servers = Server.objects.all()
        if self.instance:
            servers = servers.exclude(id=self.instance.id)

        for server in servers:
            if check_password(value, server.pin):
                raise serializers.ValidationError('Este PIN ya está en uso por otro servidor')

        return value


    def create(self, validatedData):

        ministryIds = validatedData.pop('ministryIds',[])

        server = Server.objects.create(**validatedData)

        self.assignMinistries(server,ministryIds)

        return server


    def update(self,instance,validatedData):

        ministryIds = validatedData.pop('ministryIds',None)

        for key, value in validatedData.items():
            setattr(instance, key, value)

        instance.save()

        if ministryIds is not None:

            ServerMinistry.objects.filter(server=instance).delete()

            self.assignMinistries(instance,ministryIds)

        return instance


    def assignMinistries(self,serverId,ministryIds):

        ServerMinistry.objects.filter(server=serverId).delete()

        ministries = Ministry.objects.filter(id__in=ministryIds,isActive=True)

        for ministry in ministries:

            ServerMinistry.objects.create(server=serverId,ministry=ministry)