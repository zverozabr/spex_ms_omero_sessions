import datetime
from memcached_stats import MemcachedStats
from functools import partial
from threading import Thread
from spex_common.services.Timer import every
from spex_common.modules.cache import cache_instance
import spex_common.modules.omeroweb as omero_web
import spex_common.modules.omero_blitz as omero_blitz


def refresher(service, get, get_key, host, port):
    try:
        print(f'connect to memcached for {service}')

        mem = MemcachedStats(host, port)
        key_prefix = get_key('')
        keys = list(filter(lambda item: item.startswith(key_prefix), set(mem.keys())))

        print(f'found keys {service}: {len(keys)}')

        for key in keys:
            value = cache_instance().get(key)
            now = datetime.datetime.now()
            timestamp = now.strftime("%H:%M:%S")

            if value is None:
                print(f'{timestamp}: Session {service} {key} deleted before')
                continue

            if value.active_until is not None and value.active_until < datetime.datetime.now():
                cache_instance().delete(key)
                print(f'{timestamp}: Session {service} {key} deleted')
                continue

            _, login = key.split(key_prefix)
            session = get(login)
            if session is None:
                cache_instance().delete(key)
                print(f'{timestamp}: Session {service} {key} deleted')
                continue

            print(f'{timestamp}: Session {service} {key} refreshed valid until {value.active_until}')
    except Exception as error:
        print('Error:', error)
    pass


class OmeroWebRefresherWorker(Thread):
    def __init__(self, host, port):
        super().__init__()
        self.__host = host
        self.__port = port

    def run(self):
        checker = partial(
            refresher,
            self.__class__.__name__,
            omero_web.get,
            omero_web.get_key,
            self.__host,
            self.__port
        )
        every(60, checker)


class OmeroBlitzRefresherWorker(Thread):
    def __init__(self, host, port):
        super().__init__()
        self.__host = host
        self.__port = port

    def run(self):
        checker = partial(
            refresher,
            self.__class__.__name__,
            omero_blitz.get,
            omero_blitz.get_key,
            self.__host,
            self.__port
        )
        every(60, checker)
