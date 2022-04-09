import os
import hashlib
import base64
import urllib
import string
import numbers
import threading
import errno
import fnmatch
import json

def makedirs_p(dirname, mode = None, reason = None):
    """
    Create a directory tree, ignoring an error if it already exists

    :param str pathname: directory tree to crate
    :param int mode: mode set the directory to
    """
    try:
        os.makedirs(dirname)
        # yes, this is a race condition--but setting the umask so
        # os.makedirs() gets the right mode would interfere with other
        # threads and processes.
        if mode:
            os.chmod(dirname, mode)
    except OSError as e:
        if not os.path.isdir(dirname):
            raise RuntimeError("%s: path for %s is not a directory: %s"
                               % (dirname, reason, e))
        if not os.access(dirname, os.W_OK):
            raise RuntimeError("%s: path for %s does not allow writes: %s"
                               % (dirname, reason, e))

def flat_keys_to_dict(d):
    """
    Given a dictionary of flat keys, convert it to a nested dictionary

    Similar to :func:`flat_slist_to_dict`, differing in the
    keys/values being in a dictionary.

    A key/value:

    >>> d["a.b.c"] = 34

    means:

    >>> d['a']['b']['c'] = 34

    Key in the input dictonary are processed in alphabetical order
    (thus, key a.a is processed before a.b.c); later keys override
    earlier keys:

    >>> d['a.a'] = 'aa'
    >>> d['a.a.a'] = 'aaa'
    >>> d['a.a.b'] = 'aab'

    will result in:

    >>> d['a']['a'] = { 'a': 'aaa', 'b': 'aab' }

    The

    >>> d['a.a'] = 'aa'

    gets overriden by the other settings

    :param dict d: dictionary of keys/values
    :returns dict: (nested) dictionary
    """
    tr = {}

    for key in sorted(d.keys()):
        _key_rep(tr, key, key, d[key])

    return tr

def rm_f(filename):
    """
    Remove a file (not a directory) unconditionally, ignore errors if
    it does not exist.
    """
    try:
        os.unlink(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def mkid(something, l = 10):
    """
    Generate a 10 character base32 ID out of an iterable object

    :param something: anything from which an id has to be generate
      (anything iterable)
    """
    if isinstance(something, str):
        h = hashlib.sha512(something.encode('utf-8'))
    else:
        h = hashlib.sha512(something)
    return base64.b32encode(h.digest())[:l].lower().decode('utf-8', 'ignore')

class fsdb_c(object):
    """
    This is a very simple key/value flat database

    - sets are atomic and forcefully remove existing values
    - values are just strings
    - value are limited in size to 1K
    - if a field does not exist, its value is *None*

    The key space is flat, but with a convention of periods dividing
    fields, so that:

      l['a.b.c'] = 3

    is the equivalent to:

      l['a']['b']['c'] = 3

    it also makes it way faster and easier to filter for fields.

    This will be used to store data for each target; for implemntation
    examples, look at :class:`commonl.fsdb_symlink_c`.
    """
    class exception(Exception):
        pass

    def keys(self, pattern = None):
        """
        List the fields/keys available in the database

        :param str pattern: (optional) pattern against the key names
          must match, in the style of :mod:`fnmatch`. By default, all
          keys are listed.

        :returns list: list of keys
        """
        raise NotImplementedError

    def get_as_slist(self, *patterns):
        """
        Return a sorted list of tuples *(KEY, VALUE)*\s available in the
        database.

        :param list(str) patterns: (optional) list of patterns of fields
          we must list in the style of :mod:`fnmatch`. By default, all
          keys are listed.

        :returns list(str, str): list of *(KEY, VALUE)* sorted by
          *KEY* (so *a.b.c*, representing *['a']['b']['c']* goes
          after *a.b*, representing *['a']['b']*).
        """
        raise NotImplementedError

    def get_as_dict(self, *patterns):
        """
        Return a dictionary of *KEY/VALUE*\s available in the
        database.

        :param str pattern: (optional) pattern against the key names
          must match, in the style of :mod:`fnmatch`. By default, all
          keys are listed.

        :returns dict: keys and values in dictionary form
        """
        raise NotImplementedError

    def set(self, key, value, force = True):
        """
        Set a value for a key in the database unless *key* already exists

        :param str key: name of the key to set

        :param str value: value to store; *None* to remove the field;
          only *string*, *integer*, *float* and *boolean* types

        :parm bool force: (optional; default *True*) if *key* exists,
          force the new value

        :return bool: *True* if the new value was set correctly;
          *False* if *key* already exists and *force* is *False*.
        """
        assert isinstance(value, (NoneType, str, int, float, bool)), \
            f"value must be None, str, int, float, bool; got {type(value)}"


    def get(self, key, default = None):
        """
        Return the value stored for a given key

        :param str key: name of the key to retrieve

        :param str default: (optional) value to return if *key* is not
          set; defaults to *None*.

        :returns str: value associated to *key* if *key* exists;
          otherwise *default*.
        """
        raise NotImplementedError

    @staticmethod
    def create(cache_dir):
        """
        Create with the right type for the host OS

        Same params as :class:`fsdb_symlink_c`

        Note there are catchas for atomicity; read the docs for:

        - :class:`fsdb_symlink_c`
        - :class:`fsdb_file_c`
        """
        if sys.platform in ( 'linux', 'macos' ):
            return fsdb_symlink_c(cache_dir)
        else:
            return fsdb_file_c(cache_dir)


class fsdb_symlink_c(fsdb_c):
    """
    This implements a database by storing data on the destination
    argument of a Unix symbolic link

    Creating a symlink, takes only one atomic system call, which fails
    if the link already exists. Same to read it. Thus, for small
    values, it is very efficient.
    """
    class invalid_e(fsdb_c.exception):
        pass

    def __init__(self, dirname, use_uuid = None, concept = "directory"):
        """
        Initialize the database to be saved in the give location
        directory

        :param str location: Directory where the database will be kept
        """
        if not os.path.isdir(dirname):
            raise self.invalid_e("%s: invalid %s"
                                 % (os.path.basename(dirname), concept))
        if not os.access(dirname, os.R_OK | os.W_OK | os.X_OK):
            raise self.invalid_e("%s: cannot access %s"
                                 % (os.path.basename(dirname), concept))

        if use_uuid == None:
            self.uuid = mkid(str(id(self)) + str(os.getpid()))
        else:
            self.uuid = use_uuid

        self.location = dirname

    def _raw_valid(self, location):
        return os.path.islink(location)

    def _raw_read(self, location):
        return os.readlink(location)

    def _raw_write(self, location, value):
        os.symlink(value, location)

    def _raw_unlink(self, location):
        os.unlink(location)

    def _raw_rename(self, location_new, location):
        os.replace(location_new, location)

    @staticmethod
    def _raw_stat(location):
        return os.lstat(location)

    def keys(self, pattern = None):
        l = []
        for _rootname, _dirnames, filenames_raw in os.walk(self.location):
            filenames = []
            for filename_raw in filenames_raw:
                # need to filter with the unquoted name...
                filename = urllib.parse.unquote(filename_raw)
                if pattern == None or fnmatch.fnmatch(filename, pattern):
                    if self._raw_valid(os.path.join(self.location, filename_raw)):
                        l.append(filename)
        return l

    def get_as_slist(self, *patterns):
        fl = []
        for _rootname, _dirnames, filenames_raw in os.walk(self.location):
            filenames = {}
            for filename in filenames_raw:
                filenames[urllib.parse.unquote(filename)] = filename
            if patterns:	# that means no args given
                use = {}
                for filename, filename_raw in filenames.items():
                    if field_needed(filename, patterns):
                        use[filename] = filename_raw
            else:
                use = filenames
            for filename, filename_raw in use.items():
                if self._raw_valid(os.path.join(self.location, filename_raw)):
                    bisect.insort(fl, ( filename, self._get_raw(filename_raw) ))
        return fl

    def get_as_dict(self, *patterns):
        d = {}
        for _rootname, _dirnames, filenames_raw in os.walk(self.location):
            filenames = {}
            for filename in filenames_raw:
                filenames[urllib.parse.unquote(filename)] = filename
            if patterns:	# that means no args given
                use = {}
                for filename, filename_raw in filenames.items():
                    if field_needed(filename, patterns):
                        use[filename] = filename_raw
            else:
                use = filenames
            for filename, filename_raw in use.items():
                if self._raw_valid(os.path.join(self.location, filename_raw)):
                    d[filename] = self._get_raw(filename_raw)
        return d

    def set(self, key, value, force = True):
        # escape out slashes and other unsavory characters in a non
        # destructive way that won't work as a filename
        key_orig = key
        key = urllib.parse.quote(
            key, safe = '-_ ' + string.ascii_letters + string.digits)
        location = os.path.join(self.location, key)
        if value != None:
            # the storage is always a string, so encode what is not as
            # string as T:REPR, where T is type (b boolean, n number,
            # s string) and REPR is the textual repr, json valid
            if isinstance(value, bool):
                # do first, otherwise it will test as int
                value = "b:" + str(value)
            elif isinstance(value, numbers.Integral):
                # sadly, this looses precission in floats. A lot
                value = "i:%d" % value
            elif isinstance(value, numbers.Real):
                # sadly, this can loose precission in floats--FIXME:
                # better solution needed
                value = "f:%.10f" % value
            elif isinstance(value, str):
                if value.startswith("i:") \
                   or value.startswith("f:") \
                   or value.startswith("b:") \
                   or value.startswith("s:") \
                   or value == "":
                    value = "s:" + value
            else:
                raise ValueError("can't store value of type %s" % type(value))
            assert len(value) < 4096
        if value == None:
            # note that we are setting None (aka: removing the value)
            # we also need to remove any "subfield" -- KEY.a, KEY.b
            try:
                self._raw_unlink(location)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
            # FIXME: this can be optimized a lot, now it is redoing a
            # lot of work
            for key_itr in self.keys(key_orig + ".*"):
                key_itr_raw = urllib.parse.quote(
                    key_itr, safe = '-_ ' + string.ascii_letters + string.digits)
                location = os.path.join(self.location, key_itr_raw)
                try:
                    self._raw_unlink(location)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
            return True	# already wiped by someone else
        if force == False:
            try:
                self._raw_write(location, value)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
                # ignore if it already exists
                return False
            return True

        # New location, add a unique thing to it so there is no
        # collision if more than one process is trying to modify
        # at the same time; they can override each other, that's
        # ok--the last one wins.
        location_new = location + "-" + str(os.getpid()) + "-" + str(threading.get_ident())
        rm_f(location_new)
        self._raw_write(location_new, value)
        self._raw_rename(location_new, location)
        return True

    def _get_raw(self, key, default = None):
        location = os.path.join(self.location, key)
        try:
            value = self._raw_read(location)
            # if the value was type encoded (see set()), decode it;
            # otherwise, it is a string
            if value.startswith("i:"):
                return json.loads(value.split(":", 1)[1])
            if value.startswith("f:"):
                return json.loads(value.split(":", 1)[1])
            if value.startswith("b:"):
                val = value.split(":", 1)[1]
                if val == "True":
                    return True
                elif val == "False":
                    return False
                raise ValueError("fsdb %s: key %s bad boolean '%s'"
                                 % (self.location, key, value))
            if value.startswith("s:"):
                # string that might start with s: or empty
                return value.split(":", 1)[1]
            return value	# other string
        except OSError as e:
            if e.errno == errno.ENOENT:
                return default
            raise

    def get(self, key, default = None):
        # escape out slashes and other unsavory characters in a non
        # destructive way that won't work as a filename
        key = urllib.parse.quote(
            key, safe = '-_ ' + string.ascii_letters + string.digits)
        return self._get_raw(key, default = default)

def field_needed(field, projections):
    """
    Check if the name *field* matches any of the *patterns* (ala
    :mod:`fnmatch`).

    :param str field: field name
    :param list(str) projections: list of :mod:`fnmatch` patterns
      against which to check field. Can be *None* and *[ ]* (empty).

    :returns bool: *True* if *field* matches a pattern in *patterns*
      or if *patterns* is empty or *None*. *False* otherwise.
    """
    if projections:
        # there is a list of must haves, check here first
        for projection in projections:
            if fnmatch.fnmatch(field, projection):
                return True	# we need this field
            # match projection a to fields a.[x.[y.[...]]]
            if field.startswith(projection + "."):
                return True
        return False		# we do not need this field
    else:
        return True	# no list, have it
