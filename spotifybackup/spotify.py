from urllib.parse import urlencode
from pprint import pprint

import requests

from spotifybackup.database import DatabaseClient
from spotifybackup.auth_server import AuthorisationServer


class SpotifyClient:
    def __init__(self, client_id, client_secret):
        self._client_id = client_id
        self._client_secret = client_secret
        self._api_url = 'https://api.spotify.com/v1/'
        self._db_client = DatabaseClient()
        self._access_token = self._db_client.get_value('access_token')
        self._user_id = None

    def _api_query_request(self, endpoint, data=None):
        auth_header = {
            'Authorization': f'Bearer {self._access_token}'
        }
        response = requests.get(f'{self._api_url}{endpoint}', headers=auth_header, params=data)

        if response.status_code == 200:
            return response.json()
        else:
            # TODO handle request error
            pass

    def _api_update_requests(self, endpoint, data):
        auth_header = {
            'Authorization': f'Bearer {self._access_token}'
        }
        response = requests.post(f'{self._api_url}{endpoint}', headers=auth_header, data=data)

        if response.status_code == 200:
            return response.json()
        else:
            # TODO handle request error
            pass

    def authorise(self):
        redirect_uri = f'http://localhost:8080/callback'

        if self._access_token is None:
            data = {
                'client_id': self._client_id,
                'response_type': 'code',
                'redirect_uri': redirect_uri,
                'scope': 'user-library-read playlist-read-private playlist-modify-public playlist-modify-private'
            }
            query_string = urlencode(data, doseq=True)

            print('No existing authorisation code found, use the link below to authorise this application.')
            print(f'https://accounts.spotify.com/authorize?{query_string}')

            auth_server = AuthorisationServer()
            auth_code = auth_server.start()

        token_request_data = {
            'grant_type': 'authorization_code',
            'code': self._access_token,
            'redirect_uri': redirect_uri
        }
        token_request_response = requests.post('https://accounts.spotify.com/api/token',
                                               data=token_request_data,
                                               auth=(self._client_id, self._client_secret))

        if token_request_response.status_code == 200:
            response_data = token_request_response.json()
            self._db_client.set_value('access_token', response_data['access_token'])
            self._db_client.set_value('refresh_token', response_data['refresh_token'])
            self._access_token = response_data['access_token']
            self._user_id = self._api_query_request('me')['id']

    def get_user_playlists(self):
        playlists = self._api_query_request('me/playlists')
        return playlists['items']

    def make_playlist(self, playlist_name):
        endpoint = f''
