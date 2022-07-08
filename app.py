import os
import json
import ast
import datetime
import tornado.httpserver
import tornado.options
import tornado.ioloop
import tornado.web
import tornado.wsgi

from tornado import gen, web, template

from queries import pool
import queries

tornado.options.define('port', default='8000', help='REST API Port', type=int)

class BaseHandler(tornado.web.RequestHandler):
    """
    Base handler gonna to be used instead of RequestHandler
    """
    def write_error(self, status_code, **kwargs):
        if status_code in [403, 404, 500, 503]:
            self.write('Error %s' % status_code)
        else:
            self.write('BOOM!')

class ErrorHandler(tornado.web.ErrorHandler, BaseHandler):
    """
    Default handler gonna to be used in case of 404 error
    """
    pass

class BooksHandler(BaseHandler):

    def initialize(self):
        database_url = os.environ['BOOKS_DB_CONN']
        self.session = queries.TornadoSession(uri=database_url)

    """
    GET handler for fetching numbers from database
    """
    @gen.coroutine
    def get(self):
        try:
            sql = "SELECT array_to_json(array_agg(row_to_json(json))) json FROM (SELECT bookid, title, book_info FROM books ORDER BY title) as json;"
            results = yield self.session.query(sql, {})
            data_ret = results.as_dict()
            results.free()
            print(data_ret)
            self.set_status(200)
            self.write({'message': 'All books sorted by title', 'books': data_ret['json']})
            self.finish()
        except (queries.DataError, queries.IntegrityError) as error:
            print(error)
            self.set_status(500)
            self.write({'message': 'Error getting books', 'books': [] })
            self.finish()

    """
    POST handler for adding a new book to the database
    """
    @gen.coroutine   
    def post(self):

        book_json            = self.request.body.decode('utf-8')
        if (book_json == None or book_json == ''):
            self.set_status(200)
            self.write({'message': 'Book data is missing', 'book': {}})
            self.finish()
            return

        try:
            book_json = tornado.escape.json_decode(book_json)
        except (Exception) as e:
            self.set_status(500)
            self.write({'message': 'Error: Book data is not in valid JSON format', 'book': {} })
            self.finish()
            return

        if 'title' not in book_json:
            self.set_status(200)
            self.write({'message': 'Error: book data is missing title, no book was created', 'book': {} })
            self.finish()
            return
        book_json['book_info'] = book_json.get('book_info', {})

        try:
            sql = "INSERT INTO public.books(title, book_info) VALUES (%(book_title)s, %(book_info)s) RETURNING json_build_object('title', title, 'book_info', book_info);"
            results = yield self.session.query(sql, {'book_title': book_json['title'], 'book_info': tornado.escape.json_encode(book_json['book_info'])})
            data_ret = results.as_dict()
            results.free()
            self.set_status(201)
            self.write({'message': 'Book added', 'book': data_ret['json_build_object']})
            self.finish()
        except (queries.DataError, queries.IntegrityError) as error:
            print(error)
            self.set_status(500)
            self.write({'message': 'Error: no book with that id exists', 'book': {} })
            self.finish()

class BookHandler(BaseHandler):

    def initialize(self):
        database_url = os.environ['BOOKS_DB_CONN']
        self.session = queries.TornadoSession(uri=database_url)

    """
    GET handler for fetching numbers from database
    """
    @gen.coroutine
    def get(self, **params):
        try:
            sql = "SELECT row_to_json(json) json FROM (SELECT bookid, title, book_info FROM books WHERE bookid = %(book_id)s) as json;"
            results = yield self.session.query(sql, {'book_id': params['id']})
            data_ret = results.as_dict()
            results.free()
            self.set_status(200)
            self.write({'message': 'Book with id ' + params['id'], 'book': data_ret['json']})
            self.finish()
        except (queries.DataError, queries.IntegrityError) as error:
            print(error)
            self.set_status(500)
            self.write({'message': 'Error: no book with that id exists', 'book': {} })
            self.finish()

def make_app():
    settings = dict(
        cookie_secret=str(os.urandom(45)),
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        default_handler_class=ErrorHandler,
        default_handler_args=dict(status_code=404)
    )
    return tornado.web.Application([
        (r"/api/books", BooksHandler),
        (r"/api/book/(?P<id>[^\/]+)", BookHandler),
        ], **settings)

def main():
    app = make_app()
    return app

app = main()

if __name__ == '__main__':
    print("starting tornado server..........")
    app.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.current().start()
