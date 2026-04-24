from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    class Roles(models.TextChoices):
        PASTOR = 'PASTOR', 'Pastor'
        LIDER = 'LIDER', 'Líder'

    role = models.CharField(max_length=20, choices=Roles.choices)