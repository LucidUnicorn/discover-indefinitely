from urllib.parse import urlencode

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

    def _api_update_request(self, endpoint, data):
        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(f'{self._api_url}{endpoint}', headers=headers, json=data)
        print(response.text)

        if response.status_code == 200:
            return response.json()
        else:
            # TODO handle request error
            pass

    def authorise(self):
        redirect_uri = f'http://localhost:8080/callback'
        token_request_data = {
            'grant_type': 'authorization_code',
            'code': self._access_token,
            'redirect_uri': redirect_uri
        }

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
            token_request_data['code'] = auth_server.start()

            token_request_response = requests.post('https://accounts.spotify.com/api/token',
                                                   data=token_request_data,
                                                   auth=(self._client_id, self._client_secret))

            if token_request_response.status_code == 200:
                response_data = token_request_response.json()
                self._db_client.set_value('access_token', response_data['access_token'])
                self._db_client.set_value('refresh_token', response_data['refresh_token'])
                self._access_token = response_data['access_token']

    def refresh_authorisation(self):
        pass

    def _get_user_id(self):
        return self._api_query_request('me')['id']

    def get_user_playlists(self):
        playlists = self._api_query_request('me/playlists')
        return playlists['items']

    def make_playlist(self, playlist_name):
        endpoint = f'users/{self._get_user_id()}/playlists'
        data = {
            'name': playlist_name,
            'public': False,
            'collaborative': False,
            'description': 'A backup of tracks added to Discover Weekly and Release Radar playlists.'
        }

        return self._api_update_request(endpoint, data)

    def get_playlist_tracks(self, playlist):
        playlist_id = playlist['id']
        endpoint = f'playlists/{playlist_id}/tracks'
        data = {
            'market': 'from_token'
        }

        return self._api_query_request(endpoint, data)['items']

    def add_tracks_to_playlist(self, tracks, playlist):
        playlist_id = playlist['id']
        endpoint = f'playlists/{playlist_id}/tracks'
        data = {
            'uris': tracks
        }
        self._api_update_request(endpoint, data)
