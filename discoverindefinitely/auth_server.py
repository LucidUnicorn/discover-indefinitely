import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from multiprocessing import Process, Manager
from urllib.parse import urlparse


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self._manager = None
        super().__init__(*args, **kwargs)

    def log_request(self, *args, **kwargs):
        """
        Overrides the parent to prevent request logs being printed.

        :param args:
        :param kwargs:
        """
        pass

    def do_GET(self):
        """
        If the application is not already authorised against the user's Spotify account then a callback URL is required
        by the API's authorisation flow. The callback from the API contains an access code that the application requires
        for the next stage of the authorisation flow.

        This server will only run when the callback is required. When hit, the server retrieves the access code from the
        GET parameters and informs the user that they can close the window. The access code is stored by the process
        manager so it can be retrieved by the `discoverindefinitely` process.
        """
        if self.path.startswith('/callback'):
            query = urlparse(self.path).query

            try:
                parameters = dict(pair.split('=') for pair in query.split('&'))
            except ValueError:
                response_code = 400
                message = 'Invalid query parameters'
            else:
                if 'code' in parameters:
                    response_code = 200
                    message = 'Authorisation complete, you can now close this window.'
                    self.server.complete.value = True
                    self.server.success.value = True
                    self.server.auth_code.value = parameters['code']
                elif 'error' in parameters:
                    response_code = 200
                    message = 'Authorisation failed please try again.'
                    self.server.success.value = False
                else:
                    response_code = 400
                    message = '`error` and `code` missing from query parameters.'
        else:
            response_code = 404
            message = 'Invalid endpoint'

        self.send_response(response_code)
        self.end_headers()
        self.wfile.write(message.encode())


class Server(HTTPServer):
    def __init__(self, *args, **kwargs):
        self.complete = None
        self.auth_code = None
        self.success = None
        super().__init__(*args, **kwargs)

    def serve_forever(self, *args, **kwargs):
        """
        Overrides the parent `serve_forever` in order to feed in variables from the server's process manger. These
        variables are used to track the authorisation progress and return the access code once complete.

        :param args:
        :param kwargs:
        """
        self.complete = kwargs['complete']
        self.auth_code = kwargs['auth_code']
        self.success = kwargs['success']
        kwargs = {}
        super().serve_forever(*args, **kwargs)


class AuthorisationServer:
    @staticmethod
    def _serve(complete, auth_code, success):
        """
        Runs `Server` on port 8080 to serve the API callback endpoint.

        :param complete:
        :param auth_code:
        :param success:
        """
        server = Server(('0.0.0.0', 8080), RequestHandler)
        server.serve_forever(complete=complete, auth_code=auth_code, success=success)

    def start(self):
        """
        When the API authorisation flow requires the callback URL a basic HTTP server is started on port 8080. The
        server is run as a separate process to allow it to be easily terminated once the authorisation flow is ready to
        proceed to the next step. A process manager is used to track the authorisation process state. When the API
        callback is received and the access code is stored by the manager and the server process is terminated.

        :return:
        """
        manager = Manager()
        complete = manager.Value('b', False)
        success = manager.Value('b', False)
        auth_code = manager.Value('s', '')
        process = Process(target=self._serve, args=(complete, auth_code, success))
        process.start()

        while not complete.value:
            time.sleep(0.5)

        process.terminate()
        return auth_code.value
