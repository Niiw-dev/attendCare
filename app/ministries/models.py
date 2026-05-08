from django.db import models
from users.models import User


class Ministry(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    leaderAssigned = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,
                                       limit_choices_to={'role': 'LIDER'})
    isActive = models.BooleanField(default=True)
    createdAt = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.name