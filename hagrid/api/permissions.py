from rest_framework import permissions


class IsSafeMethodOnly(permissions.BasePermission):
    """
    Even authenticated users are not allowed any methods besides safe_methods (GET, HEAD; OPTIONS)
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        else:
            return False
