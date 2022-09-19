# spex/microservices/ms-omero-proxy

## Deployment

1. Memcached

`$ docker run --name spex_memcached -p 11211:11211 -d memcached memcached -m 64`

3. Copy `.env.development` to `.env.development.local`

5. Set the following variables:
```
OMERO_HOST=<Correct host>
OMERO_WEB=http:<Correct web host>

DATA_STORAGE=<YOUR DATA_STORAGE Location>
```

6. Run server
```
$ pip install pipenv 
$ pipenv install --system --deploy --ignore-pipfile
$ pipenv shell
$ export MODE=development
$ python ./app.py
```
