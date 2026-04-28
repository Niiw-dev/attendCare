from rest_framework.permissions import BasePermission

class IsPastor(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'PASTOR'