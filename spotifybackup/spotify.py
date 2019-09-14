import math
import time
from urllib.parse import urlencode

import requests

from spotifybackup.auth_server import AuthorisationServer
from spotifybackup.database import DatabaseClient

ERROR_MSG_TOKEN_EXPIRED = 'The access token expired'


class SpotifyClient:
    def __init__(self, client_id, client_secret):
        self._client_id = client_id
        self._client_secret = client_secret
        self._api_url = 'https://api.spotify.com/v1/'
        self._db_client = DatabaseClient()
        self._access_token = self._db_client.get_value('access_token')
        self._authorise()

    def _api_query_request(self, endpoint, data=None):
        """
        Performs a GET request against the Spotify API. `endpoint` is used to determine the exact API endpoint required
        by the calling operation and if `data` is set then it is passed to the request for use as GET parameters. The
        resulting API response is returned in full.

        If the API response indicates the access token has expired the application will attempt to perform the refresh
        process automatically.

        If the API response states that the application has been rate limited it will wait for the time state in the
        `Retry-After` header plus an extra 10 seconds for safety.

        :param endpoint:
        :param data:
        :return:
        """
        auth_header = {
            'Authorization': f'Bearer {self._access_token}'
        }
        response = requests.get(f'{self._api_url}{endpoint}', headers=auth_header, params=data)
        response_data = response.json()

        if response.ok:
            return response_data
        elif response.status_code == 401 and response_data['error']['message'] == ERROR_MSG_TOKEN_EXPIRED:
            self._refresh_authorisation()
            return self._api_query_request(endpoint, data)
        elif response.status_code == 429:
            timeout = int(response.headers['Retry-After']) + 10
            print(f'Rate limited. Waiting: {timeout} seconds')
            time.sleep(timeout)
            return self._api_query_request(endpoint, data)
        else:
            print('An unexpected error has occurred')
            print(response.text)
            exit(1)

    def _api_update_request(self, endpoint, data):
        """
        Performs a POST request against the Spotify API. `endpoint` is used to determine the exact API endpoint required
        by the calling operation and if `data` is set then it is pass to the request as the JSON body. The resulting API
        response is returned in full.

        If the API response indicates the access token has expired the application will attempt to perform the refresh
        process automatically.

        If the API response states that the application has been rate limited it will wait for the time state in the
        `Retry-After` header plus an extra 10 seconds for safety.

        :param endpoint:
        :param data:
        :return:
        """
        headers = {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.post(f'{self._api_url}{endpoint}', headers=headers, json=data)
        response_data = response.json()

        if response.ok:
            return response_data
        elif response.status_code == 401 and response_data['error']['message'] == ERROR_MSG_TOKEN_EXPIRED:
            self._refresh_authorisation()
            return self._api_update_request(endpoint, data)
        elif response.status_code == 429:
            timeout = int(response.headers['Retry-After']) + 10
            print(f'Rate limited. Waiting: {timeout} seconds')
            time.sleep(timeout)
            return self._api_update_request(endpoint, data)
        else:
            print('An unexpected error has occurred')
            print(response.text)
            exit(1)

    def _authorise(self):
        """
        Performs the initial authorisation flow between the application and the Spotify API. The entire flow only has to
        run when the application is requesting authorisation from a user for the first time. Once the authorisation flow
        has been complete the application should be able to use the acquired refresh token to automatically maintain the
        authorised scope.
        """
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

    def _refresh_authorisation(self):
        """
        Uses the stored refresh token to retrieve an updated access token from the API when the previous token expires.
        If the API sends a new refresh token it is also updated.
        """
        refresh_token = self._db_client.get_value('refresh_token')

        if refresh_token is not None:
            refresh_request_data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token
            }
            refresh_request_response = requests.post('https://accounts.spotify.com/api/token',
                                                     data=refresh_request_data,
                                                     auth=(self._client_id, self._client_secret))

            if refresh_request_response.status_code == 200:
                response_data = refresh_request_response.json()
                self._db_client.set_value('access_token', response_data['access_token'])
                self._access_token = response_data['access_token']

                if 'refresh_token' in response_data:
                    self._db_client.set_value('refresh_token', response_data['refresh_token'])

    def _get_user_id(self):
        """
        Queries the API's /me endpoint and returns the authorised user's account ID.

        :return:
        """
        return self._api_query_request('me')['id']

    def get_user_playlists(self, offset=0, limit=50):
        """
        Retrieves all public and private playlists for the authorised user by iteratively calling the API until the all
        playlists are retrieved or until the maximum offset limit of 100 is exceeded.

        :return:
        """
        user_playlists = []
        data = {
            'offset': offset,
            'limit': limit
        }
        playlists = self._api_query_request('me/playlists', data)

        while len(playlists['items']) > 0:
            user_playlists.extend(playlists['items'])
            data['offset'] += 50

            if data['offset'] > 100:
                break
            else:
                playlists = self._api_query_request('me/playlists', data)

        return user_playlists

    def make_playlist(self, playlist_name):
        """
        Creates a new private, non-collaborative playlist named by `playlist_name`.

        :param playlist_name:
        :return:
        """
        endpoint = f'users/{self._get_user_id()}/playlists'
        data = {
            'name': playlist_name,
            'public': False,
            'collaborative': False,
            'description': 'A backup of tracks added to Discover Weekly and Release Radar playlists.'
        }

        return self._api_update_request(endpoint, data)

    def get_playlist_tracks(self, playlist, fields=None, offset=0, limit=100):
        """
        Given a `playlist` object from the Spotify API returns the playlist's track list. `fields`, `offset` and `limit`
        can be specified to tune the query result.

        `fields` should be a valid field query as defined in the Spotify API documentation.

        `offset` is a 0-index value that tells the API which track within the playlist it should start returning from.

        `limit` specifies the maximum number of tracks that should be returned.

        :param playlist:
        :param fields:
        :param offset:
        :param limit:
        :return:
        """
        playlist_id = playlist['id']
        endpoint = f'playlists/{playlist_id}/tracks'
        data = {
            'fields': fields,
            'offset': offset,
            'limit': limit,
            'market': 'from_token'
        }

        return self._api_query_request(endpoint, data)['items']

    def search_playlist(self, track_id, playlist):
        """
        Retrieves the track listing for `playlist` and iteratively searches for `track_id`. If the playlist contains
        more than 100 tracks the API will be queried multiple times with an incrementing offset value until the entire
        playlist has been exhausted. If the track is found in the playlist at any point the search it halted.

        :param track_id:
        :param playlist:
        :return:
        """
        offset = 0
        field_query = 'items(track(id))'
        tracks = self.get_playlist_tracks(playlist, fields=field_query)

        while len(tracks) > 0:
            for track in tracks:
                if track['track']['id'] == track_id:
                    return True

            offset += 100
            tracks = self.get_playlist_tracks(playlist, fields=field_query, offset=offset)

        return False

    def add_tracks_to_playlist(self, tracks, playlist):
        """
        Takes a list of Spotify track URIs and adds them to `playlist`. The API limits the number of tracks that can be
        added in a single request, therefore if more than 100 tracks are passed in the list is split up into chunks each
        containing a maximum of 100 tracks which are then sent to as multiple requests to the API.

        :param tracks:
        :param playlist:
        """
        playlist_id = playlist['id']
        endpoint = f'playlists/{playlist_id}/tracks'
        iterations = math.ceil(len(tracks) / 100)

        for i in range(iterations):
            upper_limit = (i + 1) * 100
            lower_limit = upper_limit - 100
            track_uris = tracks[lower_limit:upper_limit]
            data = {
                'uris': track_uris
            }
            self._api_update_request(endpoint, data)
