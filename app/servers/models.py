from django.db import models
from django.contrib.auth.hashers import make_password

from ministries.models import Ministry


class Server(models.Model):
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    document = models.CharField(max_length=50,unique=True,null=True,blank=True)
    fingerprint = models.CharField(max_length=255,null=True,blank=True)
    pin = models.CharField(max_length=255)
    isActive = models.BooleanField(default=True)
    ministries = models.ManyToManyField(Ministry,through='ServerMinistry',related_name='servers')


    def save(self, *args, **kwargs):

        if self.pin and not self.pin.startswith('pbkdf2_'):
            self.pin = make_password(self.pin)

        if (self.fingerprint and not self.fingerprint.startswith('pbkdf2_')):
            self.fingerprint = make_password(self.fingerprint)

        super().save(*args, **kwargs)


    def __str__(self):
        return f'{self.firstName} {self.lastName}'



class ServerMinistry(models.Model):

    server = models.ForeignKey(Server,on_delete=models.CASCADE,related_name='server_ministries')

    ministry = models.ForeignKey(Ministry,on_delete=models.CASCADE)

    joinedAt = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ('server', 'ministry')