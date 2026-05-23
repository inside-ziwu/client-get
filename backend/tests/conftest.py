import os

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests")
os.environ.setdefault("ADMIN_EMAIL", "test@example.com")
os.environ.setdefault("ADMIN_PASSWORD", "test-password")
os.environ.setdefault("DATA_SOURCE_ENCRYPTION_KEY", "test-encryption-key-0123456789abcdef")
os.environ.setdefault("INTERNAL_SERVICE_SECRET", "test-internal-secret")
os.environ.setdefault("ENGAGELAB_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("APP_ENV", "local")
