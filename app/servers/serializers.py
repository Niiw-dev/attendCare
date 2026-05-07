from rest_framework import serializers

from .models import Server, ServerMinistry
from ministries.models import Ministry


class ServerSerializer(serializers.ModelSerializer):

    ministryIds = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    ministries = serializers.SerializerMethodField()

    class Meta:

        model = Server

        fields = [
            'id',
            'firstName',
            'lastName',
            'document',
            'pin',
            'fingerprint',
            'isActive',
            'ministries',
            'ministryIds'
        ]

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

    def validate_pin(self, value):

        queryset = Server.objects.filter(pin=value)

        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
            raise serializers.ValidationError(
                'PIN ya existe'
            )

        return value

    def create(self, validatedData):

        ministryIds = validatedData.pop(
            'ministryIds',
            []
        )

        server = Server.objects.create(
            **validatedData
        )

        self.assignMinistries(
            server,
            ministryIds
        )

        return server

    def update(
        self,
        instance,
        validatedData
    ):

        ministryIds = validatedData.pop(
            'ministryIds',
            None
        )

        for key, value in validatedData.items():
            setattr(instance, key, value)

        instance.save()

        if ministryIds is not None:

            ServerMinistry.objects.filter(
                server=instance
            ).delete()

            self.assignMinistries(
                instance,
                ministryIds
            )

        return instance

    def assignMinistries(
        self,
        server,
        ministryIds
    ):

        ministries = Ministry.objects.filter(
            id__in=ministryIds,
            isActive=True
        )

        for ministry in ministries:

            ServerMinistry.objects.create(
                server=server,
                ministry=ministry
            )