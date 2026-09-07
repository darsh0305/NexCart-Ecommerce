from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailBackend(ModelBackend):

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        email=None,
        **kwargs
    ):
        UserModel = get_user_model()

        identifier = email or username or kwargs.get('email') or kwargs.get('username')

        if not identifier or not password:
            return None

        try:
            user = UserModel.objects.filter(
                Q(email__iexact=identifier) | Q(username__iexact=identifier)
            ).first()
        except Exception:
            return None

        if user and user.check_password(password):
            if self.user_can_authenticate(user):
                return user

        return None