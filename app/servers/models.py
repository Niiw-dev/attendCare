from django.db import models
from django.contrib.auth.hashers import make_password

from ministries.models import Ministry


class Server(models.Model):

    firstName = models.CharField(max_length=100)

    lastName = models.CharField(max_length=100)

    document = models.CharField(max_length=50,unique=True)

    pin = models.CharField(max_length=255)

    fingerprint = models.CharField(max_length=255)

    isActive = models.BooleanField(default=True)

    ministries = models.ManyToManyField(
        Ministry,
        through='ServerMinistry',
        related_name='servers'
    )

    def save(self, *args, **kwargs):

        if not self.pin.startswith('pbkdf2_'):
            self.pin = make_password(self.pin)

        if not self.fingerprint.startswith('pbkdf2_'):
            self.fingerprint = make_password(
                self.fingerprint
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.firstName} {self.lastName}'


class ServerMinistry(models.Model):

    server = models.ForeignKey(
        Server,
        on_delete=models.CASCADE
    )

    ministry = models.ForeignKey(
        Ministry,
        on_delete=models.CASCADE
    )

    joinedAt = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ('server', 'ministry')