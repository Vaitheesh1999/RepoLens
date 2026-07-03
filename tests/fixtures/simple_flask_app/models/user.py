"""User model."""


class User:
    """User model with basic database operations."""

    _users = {}
    _id_counter = 1

    def __init__(self, id, email, password, name=None):
        """Initialize user."""
        self.id = id
        self.email = email
        self.password = password
        self.name = name or email.split("@")[0]

    @classmethod
    def create(cls, email, password, name=None):
        """Create new user."""
        user = cls(cls._id_counter, email, password, name)
        cls._users[user.id] = user
        cls._id_counter += 1
        return user

    @classmethod
    def find_by_id(cls, user_id):
        """Find user by ID."""
        return cls._users.get(user_id)

    @classmethod
    def find_by_email(cls, email):
        """Find user by email."""
        for user in cls._users.values():
            if user.email == email:
                return user
        return None

    @classmethod
    def authenticate(cls, email, password):
        """Authenticate user with email and password."""
        user = cls.find_by_email(email)
        if user and user.password == password:
            return user
        return None

    @classmethod
    def list_all(cls):
        """List all users."""
        return list(cls._users.values())

    def update(self, data):
        """Update user attributes."""
        if "name" in data:
            self.name = data["name"]
        if "email" in data:
            self.email = data["email"]
        return self

    def delete(self):
        """Delete user."""
        if self.id in self._users:
            del self._users[self.id]

    def to_dict(self):
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
        }
