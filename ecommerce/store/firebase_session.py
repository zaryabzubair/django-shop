import pyrebase
import json
from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase, CreateError
from django.core.exceptions import SuspiciousOperation
from ecommerce.firebase_config import firebaseConfig


firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()


class FirebaseSessionStore(SessionBase):
    def __init__(self, session_key=None):
        super().__init__(session_key)

    def load(self):
        try:
            session_data = db.child('sessions').child(self.session_key).get().val()
            if session_data:
                return self.decode(session_data)
            else:
                self.create()
                return {}
        except Exception as e:
            self.create()
            return {}

    def create(self):
        while True:
            self._session_key = self._get_new_session_key()
            try:
                db.child('sessions').child(self._session_key).set(self.encode({}))
                break
            except Exception as e:
                continue

    def save(self, must_create=False):
        if must_create:
            self.create()
        session_data = self.encode(self._get_session(no_load=must_create))
        db.child('sessions').child(self.session_key).set(session_data)

    def exists(self, session_key):
        try:
            session_data = db.child('sessions').child(session_key).get().val()
            return session_data is not None
        except Exception as e:
            return False

    def delete(self, session_key=None):
        if session_key is None:
            session_key = self.session_key
        try:
            db.child('sessions').child(session_key).remove()
        except Exception as e:
            pass
