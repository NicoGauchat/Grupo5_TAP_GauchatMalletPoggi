from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_provider(self, request, provider, client_id=None):
        if provider == 'google' and not settings.GOOGLE_OAUTH_ENABLED:
            raise ImmediateHttpResponse(redirect('login'))
        return super().get_provider(request, provider, client_id=client_id)

    def pre_social_login(self, request, sociallogin):
        if not settings.GOOGLE_OAUTH_ENABLED:
            raise ImmediateHttpResponse(redirect('login'))

    def is_open_for_signup(self, request, sociallogin):
        return settings.GOOGLE_OAUTH_ENABLED and super().is_open_for_signup(request, sociallogin)

    def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
        messages.error(request, 'No se pudo completar el ingreso con Google. Volvé a intentarlo.')
        raise ImmediateHttpResponse(redirect('login'))
