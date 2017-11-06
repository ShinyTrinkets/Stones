
#- rev: v5 -
#- hash: 1RMI3F -

import itertools
import contextlib
from .base import BaseStore

try:
    import lmdb
except ModuleNotFoundError:
    print('LevelDB store requires PyPi.python.org/pypi/lmdb')
    exit(1)


class LmdbStore(BaseStore):
    """
    LMDB ‘Lightning’ Database container, compatible with Python dicts.
    Keys and values MUST be byte strings.
    """

    __slots__ = ('db', 'table')

    def __init__(self, name, table=None, encoder='cbor', encode_decode=tuple(),
            value_type=bytes, iterable=tuple(), **kwargs):
        super().__init__(encoder=encoder, encode_decode=encode_decode, value_type=value_type)
        self.db = lmdb.open(name + '.lmdb', max_dbs=9, map_size=8e12)
        self.table = self.db.open_db(table)
        if iterable or kwargs:
            self._populate(iterable, **kwargs)

    def close(self):
        self.db.close()


    def _populate(self, iterable=tuple(), **kwargs):
        with contextlib.suppress(AttributeError):
            iterable = iterable.items()
        with self.db.begin(write=True, db=self.table) as txn:
            for key, value in itertools.chain(iterable, kwargs.items()):
                txn.put(key, self._encode(value), dupdata=False)


    def get(self, key, default=None):
        with self.db.begin(db=self.table) as txn:
            encoded_value = txn.get(key, default)
            return self._decode(encoded_value) if encoded_value else default

    def put(self, key, value, overwrite=False):
        with self.db.begin(write=True, db=self.table) as txn:
            txn.put(key, self._encode(value), dupdata=False, overwrite=overwrite)

    def delete(self, key):
        with self.db.begin(write=True, db=self.table) as txn:
            return txn.delete(key)


    def __getitem__(self, key):
        with self.db.begin(db=self.table) as txn:
            encoded_value = txn.get(key)
            return self._decode(encoded_value)

    def __setitem__(self, key, value):
        with self.db.begin(write=True, db=self.table) as txn:
            txn.put(key, self._encode(value), dupdata=False)

    __delitem__ = delete


    def __contains__(self, key):
        with self.db.begin(db=self.table) as txn:
            return bool(txn.get(key))

    def __len__(self):
        with self.db.begin(db=self.table) as txn:
            return txn.stat()['entries']

    def __iter__(self):
        with self.db.begin(db=self.table) as txn:
            yield from txn.cursor().iternext(keys=True, values=False)

    def __repr__(self):
        items = dict(self.items())
        return self.__class__.__name__ + repr(items)


    def keys(self):
        keys_list = []
        with self.db.begin(db=self.table) as txn:
            for key in txn.cursor().iternext(keys=True, values=False):
                keys_list.append(key)
        return keys_list

    def values(self):
        vals_list = []
        with self.db.begin(db=self.table) as txn:
            for value in txn.cursor().iternext(keys=False, values=True):
                vals_list.append(self._decode(value))
        return vals_list

    def items(self):
        items_list = []
        with self.db.begin(db=self.table) as txn:
            for key, value in txn.cursor().iternext(keys=True, values=True):
                items_list.append((key, self._decode(value)))
        return items_list


    def update(self, iterable=tuple(), **kwargs):
        self._populate(iterable, **kwargs)

    def clear(self):
        with self.db.begin(write=True) as txn:
            txn.drop(self.table, delete=False)
