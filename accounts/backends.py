from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


User = get_user_model()


class UsernameOrEmailBackend(ModelBackend):

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        **kwargs
    ):

        if username is None or password is None:
            return None

        identifier = username.strip()

        user = None

        try:
            user = User.objects.get(
                username__iexact=identifier
            )

        except User.DoesNotExist:

            try:
                user = User.objects.get(
                    email__iexact=identifier
                )

            except User.DoesNotExist:
                return None

        except User.MultipleObjectsReturned:
            return None

        if (
            user.check_password(password)
            and self.user_can_authenticate(user)
        ):
            return user

        return None