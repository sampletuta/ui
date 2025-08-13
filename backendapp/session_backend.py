from django.contrib.sessions.backends.db import SessionStore as DatabaseSessionStore
from datetime import timedelta

class CustomSessionStore(DatabaseSessionStore):
    def get_expiry_date(self):
        """Override to ensure expiry is never None"""
        modification = self.get('_session_expiry')
        if modification is None:
            # Default to 2 weeks if no expiry is set
            modification = timedelta(seconds=1209600)
        elif isinstance(modification, int):
            modification = timedelta(seconds=modification)
        elif isinstance(modification, timedelta):
            pass
        else:
            # Fallback to default
            modification = timedelta(seconds=1209600)
        
        return modification
