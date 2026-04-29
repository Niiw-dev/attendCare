from rest_framework.permissions import BasePermission

class IsPastor(BasePermission):
    def hasPermission(self, request, view):
        return request.user.role == 'PASTOR'