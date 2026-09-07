"""
Custom middleware for NexCart application.
Handles cache control and session management.
"""

from django.utils.deprecation import MiddlewareMixin


class CacheControlMiddleware(MiddlewareMixin):
    """
    Middleware to add cache control headers to authenticated user pages.
    Prevents browser caching of user-specific content.
    """

    def process_response(self, request, response):
        """
        Add cache control headers based on authentication status.
        """
        # List of paths that should never be cached (user-specific pages)
        protected_paths = [
            '/accounts/profile/',
            '/accounts/change-password/',
            '/orders/',
            '/dashboard/',
            '/wishlist/',
            '/cart/',
        ]

        # Check if user is authenticated or path should not be cached
        if request.user.is_authenticated or any(
            request.path.startswith(path) for path in protected_paths
        ):
            # Add cache control headers to prevent caching
            response['Cache-Control'] = (
                'no-cache, no-store, must-revalidate, private'
            )
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

        return response


class SessionSecurityMiddleware(MiddlewareMixin):
    """
    Middleware to enhance session security and prevent session-related issues.
    """

    def process_request(self, request):
        """
        Verify session integrity and user authentication.
        """
        # If user is authenticated, verify they still exist and are active
        if request.user.is_authenticated:
            try:
                # Refresh user from database to ensure it's still valid
                user = request.user.__class__.objects.get(pk=request.user.pk)
                
                # If user is no longer active, clear the session
                if not user.is_active:
                    from django.contrib.auth import logout
                    logout(request)
                    
            except request.user.__class__.DoesNotExist:
                # User was deleted, clear the session
                from django.contrib.auth import logout
                logout(request)

        return None
