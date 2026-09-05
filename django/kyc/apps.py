from django.apps import AppConfig


class KycConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "kyc"
