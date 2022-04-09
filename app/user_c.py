import os
import dotenv

import db

dotenv.load_dotenv()

class User(object):
    # Where we save user data so users don't have to re-login
    state_dir = os.environ.get('STATE_DIR', '/db')

    def __init__(self, userid, fail_if_new = False, roles = None):
        path = self.create_filename(userid)
        self.userid = userid
        if not os.path.isdir(path) and fail_if_new == False:
            db.rm_f(path)	# cleanup, just in case
            db.makedirs_p(path)
        try:
            self.fsdb = db.fsdb_symlink_c(path)
        except ( AssertionError, db.fsdb_c.exception ) as e:
            if fail_if_new:
                raise self.user_not_existant_e("%s: no such user" % userid)
        self.fsdb.set('userid', userid)
        if roles:
            assert isinstance(roles, list)
            for role in roles:
                self.role_add(role)

    def to_dict(self):
        r = db.flat_keys_to_dict(self.fsdb.get_as_dict())
        r['name'] = os.path.basename(self.fsdb.location)
        return r

    def wipe(self):
        """
        Remove the knowledge of the user in the daemon, effectively
        logging it out.
        """
        shutil.rmtree(self.fsdb.location, ignore_errors = True)

    @staticmethod
    def is_authenticated():
        return True

    @staticmethod
    def is_active():
        return True

    @staticmethod
    def is_anonymous():
        return False

    def get_id(self):
        return str(self.userid)

    @staticmethod
    def create_filename(userid):
        """
        Makes a safe filename based on the user ID
        """
        filename = "_user_" + db.mkid(userid)
        return os.path.join(User.state_dir, filename)

    @staticmethod
    def search_user(userid):
        try:
            return User(userid, fail_if_new = True)
        except:
            return None
