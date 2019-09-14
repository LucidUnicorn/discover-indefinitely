# Spotify Backup
A tool to automatically backup the tracks in Spotify's Discover Weeky and Release Radar playlists.

## Setup
To get started you just need to clone this repo and create a configuration file. As this application is not hosted you'll also need to create your own Spotify application.

You can install Python dependencies by running `pip install -r requirements.txt`. 

### Create a Spotify application
1. Go to the [Spotify for Developers dashboard](https://developer.spotify.com/dashboard/applications).
1. Log in to your Spotify account and create a new application.
1. Open your application's page, click on 'Edit Settings' and add `http://localhost:8080/callback` as Redirect URI.
1. Copy the client ID and secret into your configuration file.

### Example configuration file
```json
{
    "client_id": "<your application client ID>",
    "client_secret": "<your application client secret>",
    "destination_playlist": "Backups"
}
```

## Usage
When you've create your Spotify application and configuration file you just need to run `python backup.py -c /path/to/config_file`. The first time you run the application you will need to authorise the application, giving it permission to view and update your playlists. 

You will be presented with a link to the Spotify Accounts service when the application starts. Once the application is authorised you will not have to perform this process again unless you delete the application's local SQLite database.

## Automating
It is possible to run this application automatically so you don't have to remember to manually execute it each week. Because of the way the Spotify API authorisation works, if you will need to perform the setup process on a device with access to a web browser. 

After you have authorised the application, you can move it to a different, always-on device and use something like CRON to schedule it. You can also use CRON locally if you'd prefer (and are running Linux).