"""
JWT Authentication System for BuildRunner 3.2 API

Implements user authentication, role-based access control, and settings persistence.
Provides secure token generation, validation, and user session management.
"""

import jwt
import json
import hashlib
from datetime import datetime, timedelta, UTC
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class Permission(str, Enum):
    """System permissions"""
    # Agent management
    AGENT_VIEW = "agent:view"
    AGENT_MANAGE = "agent:manage"
    AGENT_FAILOVER = "agent:failover"

    # Build management
    BUILD_VIEW = "build:view"
    BUILD_START = "build:start"
    BUILD_STOP = "build:stop"

    # Configuration
    CONFIG_VIEW = "config:view"
    CONFIG_EDIT = "config:edit"

    # User management
    USER_VIEW = "user:view"
    USER_MANAGE = "user:manage"

    # Analytics
    ANALYTICS_VIEW = "analytics:view"


@dataclass
class UserSettings:
    """User settings"""
    user_id: str
    theme: str = "light"
    notifications_enabled: bool = True
    notification_email: str = ""
    dashboard_layout: str = "default"
    custom_settings: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class User:
    """User information"""
    user_id: str
    email: str
    username: str
    password_hash: str
    role: UserRole
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    is_active: bool = True
    settings: UserSettings = field(default_factory=lambda: UserSettings(user_id=""))

    def __post_init__(self):
        """Initialize settings if not provided"""
        if not self.settings.user_id:
            self.settings.user_id = self.user_id

    def to_dict(self, include_password: bool = False) -> Dict:
        """Convert to dictionary"""
        data = {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "is_active": self.is_active,
            "settings": self.settings.to_dict()
        }

        if include_password:
            data["password_hash"] = self.password_hash

        return data

    def get_permissions(self) -> List[Permission]:
        """Get permissions for user role"""
        role_permissions = {
            UserRole.ADMIN: [p for p in Permission],
            UserRole.DEVELOPER: [
                Permission.AGENT_VIEW,
                Permission.AGENT_MANAGE,
                Permission.BUILD_VIEW,
                Permission.BUILD_START,
                Permission.BUILD_STOP,
                Permission.CONFIG_VIEW,
                Permission.ANALYTICS_VIEW,
            ],
            UserRole.VIEWER: [
                Permission.AGENT_VIEW,
                Permission.BUILD_VIEW,
                Permission.CONFIG_VIEW,
                Permission.ANALYTICS_VIEW,
            ]
        }

        return role_permissions.get(self.role, [])


@dataclass
class AuthToken:
    """Authentication token"""
    token: str
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    issued_at: datetime = field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """Check if token is expired"""
        if not self.expires_at:
            return False
        return datetime.now() > self.expires_at

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "token": self.token,
            "token_type": self.token_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "issued_at": self.issued_at.isoformat()
        }


class PasswordHasher:
    """Password hashing utility"""

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """
        Hash a password with salt

        Args:
            password: Password to hash
            salt: Optional salt (generated if not provided)

        Returns:
            Tuple of (password_hash, salt)
        """
        if not salt:
            import secrets
            salt = secrets.token_hex(16)

        # Hash password with salt
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()

        return f"{salt}${password_hash}", salt

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify a password against hash

        Args:
            password: Password to verify
            password_hash: Password hash to verify against

        Returns:
            True if password matches
        """
        try:
            salt, _ = password_hash.split('$')
            hashed, _ = PasswordHasher.hash_password(password, salt)
            return hashed == password_hash
        except Exception:
            return False


class JWTManager:
    """JWT token management"""

    def __init__(self, secret_key: str, algorithm: str = "HS256", expiration_hours: int = 24):
        """
        Initialize JWT manager

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm
            expiration_hours: Token expiration time in hours
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiration_hours = expiration_hours

    def create_token(
        self,
        user_id: str,
        email: str,
        role: UserRole,
        permissions: Optional[List[str]] = None,
        additional_claims: Optional[Dict] = None
    ) -> AuthToken:
        """
        Create JWT token

        Args:
            user_id: User ID
            email: User email
            role: User role
            permissions: List of permissions
            additional_claims: Additional JWT claims

        Returns:
            Authentication token
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=self.expiration_hours)

        payload = {
            "user_id": user_id,
            "email": email,
            "role": role.value,
            "permissions": permissions or [],
            "iat": now,
            "exp": expires_at,
            "iss": "buildrunner",
            "sub": user_id
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        return AuthToken(
            token=token,
            token_type="Bearer",
            expires_at=expires_at,
            issued_at=now
        )

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify and decode JWT token

        Args:
            token: JWT token to verify

        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
        except Exception:
            return None

    def refresh_token(self, token: str) -> Optional[AuthToken]:
        """
        Refresh an existing token

        Args:
            token: Token to refresh

        Returns:
            New token or None if refresh failed
        """
        payload = self.verify_token(token)
        if not payload:
            return None

        # Create new token with same claims
        return self.create_token(
            user_id=payload.get("user_id"),
            email=payload.get("email"),
            role=UserRole(payload.get("role", "viewer")),
            permissions=payload.get("permissions"),
        )


class AuthenticationManager:
    """Main authentication manager"""

    def __init__(
        self,
        secret_key: str,
        storage_path: Optional[Path] = None,
        expiration_hours: int = 24
    ):
        """
        Initialize authentication manager

        Args:
            secret_key: Secret key for JWT signing
            storage_path: Path to store user data
            expiration_hours: Token expiration time in hours
        """
        self.jwt_manager = JWTManager(secret_key, expiration_hours=expiration_hours)
        self.storage_path = storage_path or Path.home() / ".buildrunner" / "auth"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # In-memory user storage
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, AuthToken] = {}

        # Load users from storage
        self._load_users()

    def register_user(
        self,
        email: str,
        username: str,
        password: str,
        role: UserRole = UserRole.VIEWER
    ) -> Optional[User]:
        """
        Register a new user

        Args:
            email: User email
            username: Username
            password: Password
            role: User role

        Returns:
            Created user or None if registration failed
        """
        # Check if user already exists
        if any(u.email == email or u.username == username for u in self.users.values()):
            return None

        # Hash password
        password_hash, _ = PasswordHasher.hash_password(password)

        # Create user
        user = User(
            user_id=self._generate_user_id(),
            email=email,
            username=username,
            password_hash=password_hash,
            role=role
        )

        self.users[user.user_id] = user
        self._save_users()

        return user

    def authenticate(self, email: str, password: str) -> Optional[AuthToken]:
        """
        Authenticate user with email and password

        Args:
            email: User email
            password: User password

        Returns:
            Authentication token or None if authentication failed
        """
        # Find user by email
        user = next((u for u in self.users.values() if u.email == email), None)

        if not user or not user.is_active:
            return None

        # Verify password
        if not PasswordHasher.verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login = datetime.now()

        # Create token
        token = self.jwt_manager.create_token(
            user_id=user.user_id,
            email=user.email,
            role=user.role,
            permissions=[p.value for p in user.get_permissions()]
        )

        # Store session
        self.sessions[token.token] = token

        # Save users
        self._save_users()

        return token

    def logout(self, token: str) -> bool:
        """
        Logout user by invalidating token

        Args:
            token: Authentication token

        Returns:
            True if logout successful
        """
        if token in self.sessions:
            del self.sessions[token]
            return True
        return False

    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verify authentication token

        Args:
            token: Token to verify

        Returns:
            Token payload or None if invalid
        """
        return self.jwt_manager.verify_token(token)

    def refresh_token(self, token: str) -> Optional[AuthToken]:
        """
        Refresh authentication token

        Args:
            token: Token to refresh

        Returns:
            New token or None if refresh failed
        """
        return self.jwt_manager.refresh_token(token)

    def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            User or None if not found
        """
        return self.users.get(user_id)

    def update_user_settings(self, user_id: str, settings: Dict) -> Optional[User]:
        """
        Update user settings

        Args:
            user_id: User ID
            settings: Settings to update

        Returns:
            Updated user or None if not found
        """
        user = self.users.get(user_id)
        if not user:
            return None

        # Update settings
        for key, value in settings.items():
            if hasattr(user.settings, key):
                setattr(user.settings, key, value)
            else:
                user.settings.custom_settings[key] = value

        self._save_users()
        return user

    def list_users(self) -> List[User]:
        """
        Get all users

        Returns:
            List of users
        """
        return list(self.users.values())

    def disable_user(self, user_id: str) -> bool:
        """
        Disable a user account

        Args:
            user_id: User ID

        Returns:
            True if disabled successfully
        """
        user = self.users.get(user_id)
        if not user:
            return False

        user.is_active = False
        self._save_users()
        return True

    def enable_user(self, user_id: str) -> bool:
        """
        Enable a user account

        Args:
            user_id: User ID

        Returns:
            True if enabled successfully
        """
        user = self.users.get(user_id)
        if not user:
            return False

        user.is_active = True
        self._save_users()
        return True

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """
        Change user password

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            True if password changed successfully
        """
        user = self.users.get(user_id)
        if not user:
            return False

        # Verify old password
        if not PasswordHasher.verify_password(old_password, user.password_hash):
            return False

        # Hash new password
        password_hash, _ = PasswordHasher.hash_password(new_password)
        user.password_hash = password_hash

        self._save_users()
        return True

    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        import uuid
        return str(uuid.uuid4())

    def _save_users(self) -> None:
        """Save users to storage"""
        users_file = self.storage_path / "users.json"

        data = {
            uid: user.to_dict(include_password=True)
            for uid, user in self.users.items()
        }

        users_file.parent.mkdir(parents=True, exist_ok=True)
        with open(users_file, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_users(self) -> None:
        """Load users from storage"""
        users_file = self.storage_path / "users.json"

        if not users_file.exists():
            # Create default admin user
            admin = self.register_user(
                email="admin@buildrunner.local",
                username="admin",
                password="admin",
                role=UserRole.ADMIN
            )
            return

        try:
            with open(users_file, "r") as f:
                data = json.load(f)

            for user_id, user_data in data.items():
                user = User(
                    user_id=user_id,
                    email=user_data["email"],
                    username=user_data["username"],
                    password_hash=user_data["password_hash"],
                    role=UserRole(user_data.get("role", "viewer")),
                    created_at=datetime.fromisoformat(user_data["created_at"]),
                    last_login=datetime.fromisoformat(user_data["last_login"])
                    if user_data.get("last_login")
                    else None,
                    is_active=user_data.get("is_active", True)
                )

                if "settings" in user_data:
                    settings_data = user_data["settings"]
                    user.settings = UserSettings(
                        user_id=settings_data.get("user_id", user_id),
                        theme=settings_data.get("theme", "light"),
                        notifications_enabled=settings_data.get("notifications_enabled", True),
                        notification_email=settings_data.get("notification_email", ""),
                        dashboard_layout=settings_data.get("dashboard_layout", "default"),
                        custom_settings=settings_data.get("custom_settings", {})
                    )

                self.users[user_id] = user

        except Exception as e:
            print(f"Error loading users: {e}")
