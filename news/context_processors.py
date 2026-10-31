from django.conf import settings


def social_auth(request):
    return {"google_oauth_enabled": settings.GOOGLE_OAUTH_ENABLED}
