import spex_common.modules.omeroweb as omeroweb
import spex_common.modules.omero_blitz as omero_blitz
from os import getenv
from spex_common.config import load_config
from werkzeug.exceptions import HTTPException
from flask import Flask, request, abort
from flask_restx import Resource, Api
from flask_cors import CORS
from modules.refresher import OmeroWebRefresherWorker, OmeroBlitzRefresherWorker


config = load_config()

application = Flask(__name__)
application.config.from_mapping(config)

api = Api(application)


@api.errorhandler
@api.errorhandler(Exception)
@api.errorhandler(HTTPException)
def default_error_handler(error):
    code = getattr(error, 'code', 500)
    result = {
        'success': False,
        'code': code,
        'message': getattr(error, 'description', str(error))
    }
    return result, code


@api.route('/')
class OmeroAuth(Resource):
    def post(self):
        body = request.json

        login = body['username']
        password = body['password']
        client = omeroweb.create(login, password)
        if not client:
            abort(401, 'Unable to login user')

        client = omero_blitz.create(login, password)
        if not client:
            abort(401, 'Unable to login user')

        return {'success': True}, 200


CORS(application, supports_credentials=True)

if __name__ == '__main__':
    # init session refresher thread
    worker = OmeroWebRefresherWorker()
    worker.start()

    worker = OmeroBlitzRefresherWorker()
    worker.start()

    application.run()
