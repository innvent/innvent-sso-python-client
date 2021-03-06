# coding: utf-8
from datetime import datetime
from dateutil.parser import parse
from mock import patch, Mock

from django.conf import settings
from django.test import TestCase

from .testtools import vcr
from ..utils import SSOAPIClient, sso_hostname, remove_data_from_url


class SSOAPIClientTestCase(TestCase):

    def test_sso_client_must_have_a_correct_session_attached_to_it(self):
        client = SSOAPIClient()

        expected_auth = (settings.SSO_SERVICE_TOKEN, settings.SSO_SECRET_KEY)

        self.assertTrue(hasattr(client, '_session'))
        self.assertEqual(client._session.auth, expected_auth)

    def test_retrieve_new_token_should_return_correctly(self):
        with vcr.use_cassette('access_token_valid.json'):
            resp_dict = SSOAPIClient().retrieve_new_token()

        with vcr.use_cassette('access_token_valid.json'):
            exp_resp = SSOAPIClient()._get('/access_token', cookies={'session_id': '1234'})

        self.assertIn('token', resp_dict.keys())
        self.assertEqual(resp_dict['token'], exp_resp['token'])

        self.assertIn('expires_at', resp_dict.keys())
        expected_expires_at = parse(exp_resp['expires_at'], ignoretz=True)
        self.assertEqual(resp_dict['expires_at'], expected_expires_at)

    @patch.object(SSOAPIClient, '_request')
    def test_retrieve_new_token_should_use_sso_session_id_settings(self, mocked_method):
        mocked_method.return_value = {'expires_at': datetime.now().isoformat()}

        session_id = 'dummy_session'

        with self.settings(SSO_SESSION_ID=session_id):
            SSOAPIClient().retrieve_new_token()

        call_args = ('get', '/access_token')
        call_kwargs = {'cookies': {'session_id': session_id}, 'params': None}

        mocked_method.assert_called_once_with(*call_args, **call_kwargs)

    def test_create_user_should_return_the_user_id(self):
        with vcr.use_cassette('create_user_successful.json'):
            resp = SSOAPIClient().create_user(
                username='user',
                password='passwd',
                email='user@example.com',
                first_name='Test',
                last_name='User',
            )

        with vcr.use_cassette('create_user_successful.json'):
            post_data = {
                'login': 'user',
                'password': 'passwd',
                'email': 'user@example.com',
                'firstname': 'Test',
                'lastname': 'User'
            }

            exp_resp = SSOAPIClient()._post('/users', post_data)
            exp_dict = {'id': exp_resp['created_user_id']}

        self.assertEqual(exp_dict, resp)

    def test_get_user_should_return_the_user_correctly_by_username(self):
        with vcr.use_cassette('get_user_by_username_successful.json'):
            resp = SSOAPIClient().get_user('user')

        with vcr.use_cassette('get_user_by_username_successful.json'):
            exp_resp = SSOAPIClient()._get('/user_by_login', {'login': 'user'})
            exp_resp['username'] = exp_resp.pop('login')

        self.assertEqual(exp_resp, resp)

    def test_update_user_should_update_the_user_correctly_by_username(self):
        with vcr.use_cassette('update_user_by_username_successful.json'):
            update_resp = SSOAPIClient().update_user('user',
                first_name='User',
                last_name='Test',
            )

        self.assertTrue(update_resp)

        with vcr.use_cassette('get_user_after_update_successful.json'):
            get_user_resp = SSOAPIClient().get_user('user')

        self.assertEqual(get_user_resp['first_name'], 'User')
        self.assertEqual(get_user_resp['last_name'], 'Test')

    def test_create_or_update_user_should_return_the_user_id(self):
        with vcr.use_cassette('create_or_update_user__create.json'):
            resp = SSOAPIClient().create_or_update_user(
                username='user',
                password='passwd',
                email='user@example.com',
                first_name='Test',
                last_name='User',
            )

        self.assertTrue(resp)

    def test_create_or_update_user_should_return_the_user_id(self):
        with vcr.use_cassette('create_or_update_user__update.json'):
            resp = SSOAPIClient().create_or_update_user(
                username='user',
                password='passwd',
                email='user@example.com',
                first_name='Test',
                last_name='User',
            )

        self.assertFalse(resp)

    def test_list_users_should_return_the_correct_dict(self):
        with vcr.use_cassette('list_users.json'):
            resp = SSOAPIClient().list_users()

        self.assertIn('total_pages', resp)
        self.assertIn('count', resp)

        self.assertIn('users', resp)
        self.assertIsInstance(resp['users'], list)

    def test_add_application_should_update_user_with_the_added_application(self):
        with vcr.use_cassette('add_application_to_user_success.json'):
            resp = SSOAPIClient().add_application_to_user('sudo', 'test-app')

        self.assertTrue(resp)

        with vcr.use_cassette('get_user_after_successful_application_addition.json'):
            user = SSOAPIClient().get_user('sudo')

        self.assertIn('applications', user)
        self.assertIn('test-app', user['applications'])

    def test_failed_add_application_should_not_update_user_with_the_added_application(self):
        with vcr.use_cassette('add_application_to_user_failure.json'):
            resp = SSOAPIClient().add_application_to_user('sudo', 'Must be slug')

        self.assertFalse(resp)

        with vcr.use_cassette('get_user_after_failed_application_addition.json'):
            user = SSOAPIClient().get_user('sudo')

        self.assertIn('applications', user)
        self.assertNotIn('Must be slug', user['applications'])

    def test_remove_application_should_update_user_with_the_removed_application(self):
        with vcr.use_cassette('remove_application_from_user_success.json'):
            resp = SSOAPIClient().remove_application_from_user('sudo', 'test-app')

        self.assertTrue(resp)

        with vcr.use_cassette('get_user_after_successful_application_remove.json'):
            user = SSOAPIClient().get_user('sudo')

        self.assertIn('applications', user)
        self.assertNotIn('test-app', user['applications'])

    def test_failed_remove_application_should_not_update_user_with_the_removed_application(self):
        with vcr.use_cassette('remove_application_from_user_failure.json'):
            resp = SSOAPIClient().remove_application_from_user('sudo', 'Must be slug')

        self.assertFalse(resp)

        with vcr.use_cassette('get_user_after_failed_application_remove.json'):
            user = SSOAPIClient().get_user('sudo')

        self.assertIn('applications', user)
        self.assertNotIn('test-app', user['applications'])

    def test_list_users_should_return_the_correct_dict(self):
        with vcr.use_cassette('list_applications.json'):
            resp = SSOAPIClient().list_applications()

        self.assertIsInstance(resp, list)
        self.assertIn('default', resp)


class RemoveDataFromUrlTestCase(TestCase):

    def test_should_remove_data_query_param_from_url(self):
        expected_url = 'totally-a-url'
        url = '{0}?data=none'.format(expected_url)

        self.assertEqual(remove_data_from_url(url), expected_url)

    def test_should_not_remove_other_query_params_from_url(self):
        expected_url = 'totally-a-url?other=param'
        url = '{0}&data=none'.format(expected_url)

        self.assertEqual(remove_data_from_url(url), expected_url)

