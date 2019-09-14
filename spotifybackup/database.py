import sqlite3
from pathlib import Path


class DatabaseClient:
    def __init__(self):
        self._db_path = (Path(__file__).parent / 'db.sqlite').resolve()
        connection = self._connect()

        with connection:
            connection.execute('CREATE TABLE IF NOT EXISTS configuration (key TEXT, value TEXT)')

        connection.close()

    def _connect(self):
        return sqlite3.connect(self._db_path)

    def get_value(self, key):
        connection = self._connect()

        with connection:
            cursor = connection.cursor()
            cursor.execute('SELECT value FROM configuration WHERE key = ?', (key,))
            config_value = cursor.fetchone()

        connection.close()

        if config_value is None:
            return config_value

        return config_value[0]

    def set_value(self, key, value):
        connection = self._connect()

        with connection:
            cursor = connection.cursor()
            cursor.execute('SELECT value FROM configuration WHERE key = ?', (key,))

            if cursor.fetchone() is None:
                connection.execute('INSERT INTO configuration (key, value) VALUES (?, ?)', (key, value))
            else:
                connection.execute('UPDATE configuration SET value = ? WHERE key = ?', (value, key))

        connection.close()
