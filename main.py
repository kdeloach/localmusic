import sys
import logging
from localmusic import app

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.options import parse_command_line

parse_command_line()
http_server = HTTPServer(WSGIContainer(app))
http_server.listen(80)
IOLoop.instance().start()
