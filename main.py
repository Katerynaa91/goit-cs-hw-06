import os
import mimetypes
import pathlib
import urllib.parse
import socket
import logging
from multiprocessing import Process
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from dotenv import load_dotenv
from pymongo.errors import ConnectionFailure
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(threadName)s: %(message)s")

HOST = '127.0.0.1'
# HOST = socket.gethostbyname()
HTTP_PORT = 3000
SOCKET_PORT = 5000


class HttpHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))
        send_data_to_socket(data)
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == "/":
            self.send_html_file("static/index.html")
        elif pr_url.path == "/message" or pr_url.path == "/message.html":
            self.send_html_file("static/message.html")
        else:
            filename = pathlib.Path() /'static'/pr_url.path[1:]
            if filename.exists():
                self.send_static(filename)
            else:
                self.send_html_file('static/error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as fd:
            self.wfile.write(fd.read())

    def send_static(self, filename):
        self.send_response(200)
        mime_type, *_ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header('Content-Type', mime_type)
        else:
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())

def send_data_to_socket(data):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        server = (HOST, SOCKET_PORT)
        sock.connect(server)
        sock.sendall(data)
        logging.info("Data from Client Socket Sent")
        sock.close()


def save_data(data, db_name = "courses_db", collection = "contact_form"):
    """Функція для підлючення до БД та додавання в БД даних, отриманих через сокет"""
    load_dotenv()
    uri = os.getenv("DATABASE_URI")
    client = MongoClient(uri, server_api=ServerApi("1"))

    data_parse = urllib.parse.unquote_plus(data.decode('utf-8'))
    data_dict = {key: value for key, value in [el.split("=") for el in data_parse.split("&")]}

    try:
        client = MongoClient(uri)
        db = client[db_name]
        received_date = datetime.now()
        db[collection].insert_one({"date": received_date, "name": data_dict["username"], "message": data_dict["message"]})
    except ConnectionFailure as c:
        logging.error(f"Couldn't connect to database. ERROR: {c}")


def run_socket_server(host=HOST, port=SOCKET_PORT):
    addr = (host, port)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(addr)
    server_socket.listen()
    try:
        while True:
            conn, _ = server_socket.accept()
            data = conn.recv(1024)
            save_data(data)
    except OSError as ose:
        logging.error(f"Socket Server ERROR: {ose}")
        conn.close()
    finally:
        server_socket.close()


def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = (HOST, HTTP_PORT)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        logging.info("HTTP Server closed")
        http.server_close()


if __name__ == "__main__":

    http_server = Process(target=run_http_server)
    http_server.start()

    socket_server = Process(target=run_socket_server)
    socket_server.start()

    http_server.join()
    socket_server.join()
