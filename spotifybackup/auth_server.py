import time
from multiprocessing import Process, Manager
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse


class RequestHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self._manager = None
        super().__init__(*args, **kwargs)

    def log_request(self, *args, **kwargs):
        pass

    def do_GET(self):
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
        self.complete = kwargs['complete']
        self.auth_code = kwargs['auth_code']
        self.success = kwargs['success']
        kwargs = {}
        super().serve_forever(*args, **kwargs)


class AuthorisationServer:
    @staticmethod
    def _serve(complete, auth_code, success):
        server = Server(('0.0.0.0', 8080), RequestHandler)
        server.serve_forever(complete=complete, auth_code=auth_code, success=success)

    def start(self):
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
