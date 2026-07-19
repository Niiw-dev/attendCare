from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsPastor(BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'PASTOR'

class IsPastorOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.role == 'PASTOR'