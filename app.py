from flask import Flask, render_template
from config import Config
from routes.api import api, SHUTDOWN_TOKEN

app = Flask(__name__)
app.config.from_object(Config)

app.register_blueprint(api, url_prefix='/api')

@app.route('/')
def index():
    response = app.make_response(render_template(
        'index.html', version=Config.VERSION, shutdown_token=SHUTDOWN_TOKEN))
    # The page carries the shutdown token, so do not let it be cached or stored.
    response.headers['Cache-Control'] = 'no-store'
    return response

import os
import webbrowser
import threading

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 5000
LOOPBACK_HOSTS = {'127.0.0.1', 'localhost', '::1'}
TRUTHY = {'1', 'true', 'yes', 'on'}


def server_settings(environ=None):
    """Decide how the development/packaged server is started.

    Safe by default: only reachable from this computer, no debugger.
      HOST            bind address (default 127.0.0.1; 0.0.0.0 must be asked for)
      PORT            1-65535 (default 5000, invalid values fall back)
      RW_DEBUG        1/true/yes/on enables Flask's debugger, but only on a
                      loopback host (the debugger allows code execution)
      RW_NO_BROWSER   1/true/yes/on: do not open the browser automatically
    """
    environ = os.environ if environ is None else environ

    host = (environ.get('HOST') or '').strip() or DEFAULT_HOST

    try:
        port = int((environ.get('PORT') or '').strip())
    except ValueError:
        port = DEFAULT_PORT
    if not 1 <= port <= 65535:
        port = DEFAULT_PORT

    wants_debug = (environ.get('RW_DEBUG') or '').strip().lower() in TRUTHY
    debug = wants_debug and host in LOOPBACK_HOSTS
    if wants_debug and not debug:
        print(f"WARNING: RW_DEBUG ignored: the debugger is not allowed on host '{host}'.")
    if host not in LOOPBACK_HOSTS:
        print(f"WARNING: listening on '{host}': the app is reachable from other computers "
              "and has no login.")

    open_browser = (environ.get('RW_NO_BROWSER') or '').strip().lower() not in TRUTHY

    return {'host': host, 'port': port, 'debug': debug, 'open_browser': open_browser}


if __name__ == '__main__':
    settings = server_settings()
    if settings['open_browser']:
        url_host = 'localhost' if settings['host'] in LOOPBACK_HOSTS | {'0.0.0.0'} else settings['host']
        threading.Timer(
            1.5, lambda: webbrowser.open(f"http://{url_host}:{settings['port']}")).start()
    app.run(debug=settings['debug'], host=settings['host'], port=settings['port'])
