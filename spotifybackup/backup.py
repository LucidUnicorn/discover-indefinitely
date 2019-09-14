import json
import argparse
from pathlib import Path

from spotifybackup.spotify import SpotifyClient


def get_playlist(target_playlist, playlists):
    for playlist in playlists:
        if playlist['name'] == target_playlist:
            return playlist


def identify_tracks_to_add(client, source_playlist, destination_playlist):
    identified_tracks = []

    if source_playlist is not None:
        source_playlist_tracks = client.get_playlist_tracks(source_playlist)

        for track in source_playlist_tracks:
            track_in_destination_playlist = client.search_playlist(track['track']['id'], destination_playlist)

            if not track_in_destination_playlist:
                identified_tracks.append(track['track']['uri'])

    return identified_tracks


def main(application_config):
    client = SpotifyClient(application_config['client_id'], application_config['client_secret'])
    playlists = client.get_user_playlists()
    target_playlist = get_playlist('Backups', playlists)
    discover_weekly_playlist = get_playlist('Discover Weekly', playlists)
    release_radar_playlist = get_playlist('Release Radar', playlists)

    if target_playlist is None:
        target_playlist = client.make_playlist('Backups')

    tracks_to_add = []
    tracks_to_add.extend(identify_tracks_to_add(client, discover_weekly_playlist, target_playlist))
    tracks_to_add.extend(identify_tracks_to_add(client, release_radar_playlist, target_playlist))
    client.add_tracks_to_playlist(tracks_to_add, target_playlist)


def validate_configuration(application_config):
    if 'client_id' not in application_config:
        print('Configuration file must contain client_id')
        exit(1)
    elif 'client_secret' not in application_config:
        print('Configuration file must contain client_secret')
        exit(1)
    elif 'destination_playlist' not in application_config:
        print('Configuration file must contain destination_playlist')
        exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backup your Spotify Discover Weekly and Release Radar playlists')
    parser.add_argument('-c', '--config', help='Configuration file', default='config.json')
    args = parser.parse_args()
    config_file = Path(args.config)

    if not config_file.is_file():
        print(f'Configuration file does not exist at {config_file.resolve()}')
        exit(1)

    with config_file.open('r') as config:
        configuration = json.load(config)

    validate_configuration(configuration)
