import keyring


class MockKeyring:
    # Replaces the keyring library with a mock to not rely on a specific
    # backend for testing. Stores test credentials in memory.

    errors = keyring.errors

    def __init__(self):
        self.storage = {}

    def set_password(self, service, username, password):
        self.storage[(service, username)] = password

    def get_password(self, service, username):
        return self.storage.get((service, username))

    def delete_password(self, service, username):
        try:
            del self.storage[(service, username)]
        except KeyError as exc:
            raise keyring.errors.PasswordDeleteError(username) from exc
