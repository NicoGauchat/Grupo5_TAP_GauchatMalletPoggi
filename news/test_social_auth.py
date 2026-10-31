from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from allauth.socialaccount.models import SocialAccount, SocialToken
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse


PROVIDERS = {'google': {
    'APPS': [{'client_id': 'test-client', 'secret': 'test-secret', 'key': ''}],
    'SCOPE': ['profile', 'email'],
    'OAUTH_PKCE_ENABLED': True,
}}


@override_settings(GOOGLE_OAUTH_ENABLED=True, SOCIALACCOUNT_PROVIDERS=PROVIDERS)
class GoogleLoginTests(TestCase):
    def start_login(self, client=None, next_url=''):
        client = client or self.client
        response = client.post(reverse('google_login'), {'next': next_url})
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response.url).query)
        self.assertEqual(query['client_id'], ['test-client'])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertEqual(query['redirect_uri'], ['http://testserver/accounts/google/login/callback/'])
        return query['state'][0]

    def finish_login(self, state, client=None):
        def complete(adapter, request, app, token, **kwargs):
            return adapter.get_provider().sociallogin_from_response(request, {
                'sub': 'google-test-subject', 'email': 'persona@example.test',
                'email_verified': True, 'given_name': 'Ana', 'family_name': 'Prueba',
            })

        with patch.object(GoogleOAuth2Adapter, 'get_access_token_data', return_value={'access_token': 'test-token'}), patch.object(GoogleOAuth2Adapter, 'complete_login', complete):
            return (client or self.client).get(reverse('google_callback'), {'state': state, 'code': 'test-code'})

    def test_button_and_confirmation_use_post(self):
        self.assertContains(self.client.get(reverse('login')), 'Continuar con Google')
        response = self.client.get(reverse('google_login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Google compartirá tu nombre')
        self.assertNotIn('socialaccount_states', self.client.session)
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('google_login')).status_code, 403)

    @override_settings(GOOGLE_OAUTH_ENABLED=False)
    def test_disabled_provider_keeps_local_login_available(self):
        self.assertNotContains(self.client.get(reverse('login')), 'Continuar con Google')
        self.assertRedirects(self.client.post(reverse('google_login')), reverse('login'))
        self.assertRedirects(self.client.get(reverse('google_callback')), reverse('login'))

    def test_signup_repeat_login_and_no_token_storage(self):
        response = self.finish_login(self.start_login())
        self.assertRedirects(response, reverse('preferences'))
        user = get_user_model().objects.get(email='persona@example.test')
        self.assertEqual(user.first_name, 'Ana')
        self.assertFalse(user.has_usable_password())
        self.assertEqual(str(user.pk), self.client.session['_auth_user_id'])
        self.assertEqual(SocialAccount.objects.count(), 1)
        self.assertFalse(SocialToken.objects.exists())
        self.client.post(reverse('logout'))
        self.assertRedirects(self.finish_login(self.start_login()), reverse('news_feed'))
        self.assertEqual(get_user_model().objects.count(), 1)

    def test_unsafe_next_is_not_followed(self):
        response = self.finish_login(self.start_login(next_url='https://evil.example/'))
        self.assertRedirects(response, reverse('preferences'))

    def test_state_is_required_and_bound_to_browser(self):
        state = self.start_login()
        for client, value in [(self.client, 'tampered'), (Client(), state)]:
            response = self.finish_login(value, client)
            self.assertRedirects(response, reverse('login'))
            self.assertNotIn('_auth_user_id', client.session)
        self.assertFalse(get_user_model().objects.exists())

    def test_cancelled_flow_returns_to_login(self):
        response = self.client.get(reverse('google_callback'), {
            'state': self.start_login(), 'error': 'access_denied',
        })
        self.assertRedirects(response, reverse('login'))
        self.assertFalse(get_user_model().objects.exists())

    def test_matching_email_does_not_log_into_existing_account(self):
        user = get_user_model().objects.create_user('existing', email='persona@example.test', password='test-pass-strong')
        response = self.finish_login(self.start_login())
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertFalse(SocialAccount.objects.filter(user=user).exists())
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(response.status_code, 302)

    def test_local_registration_and_login_still_work(self):
        response = self.client.post(reverse('register'), {
            'username': 'local-user', 'first_name': 'Nombre',
            'password1': 'local-pass-strong-42', 'password2': 'local-pass-strong-42',
        })
        self.assertRedirects(response, reverse('preferences'))
        self.client.post(reverse('logout'))
        response = self.client.post(reverse('login'), {'username': 'local-user', 'password': 'local-pass-strong-42'})
        self.assertRedirects(response, reverse('news_feed'))
