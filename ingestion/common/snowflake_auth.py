"""
Shared Snowflake key pair authentication helper for all Python scripts
that connect to Snowflake in this project.

WHY KEY PAIR AUTH
-----------------
Snowflake is deprecating password-only authentication with enforcement
beginning August-October 2026. Key pair auth (RSA private key) is the
recommended replacement and is more secure: the private key never leaves
the local machine, unlike a password that is transmitted on every
connection attempt.

MIRRORING dbt profiles.yml
---------------------------
The dbt profiles.yml at ~/.dbt/profiles.yml was migrated to key pair auth
first, via its `private_key_path` field referencing SNOWFLAKE_PRIVATE_KEY_PATH.
This module applies the identical pattern to the Python ingestion scripts and
analyses so every Snowflake connection in the project uses a consistent auth
mechanism. One key, one pattern, one place to update.

EXPECTED SETUP
--------------
- Private key format: unencrypted PKCS#8 RSA key (.p8 file)
- Location: set SNOWFLAKE_PRIVATE_KEY_PATH in .env (see .env.example)
- Default path used in this project:
    /home/hemu/.config/snowflake/keys/snowflake_key.p8
- Generate a key pair via Snowflake docs:
    https://docs.snowflake.com/en/user-guide/key-pair-auth
"""

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def load_private_key(path: str) -> bytes:
    """Load an unencrypted PKCS#8 RSA private key and return DER-encoded bytes.

    The returned bytes are passed directly to snowflake.connector.connect()
    as the ``private_key`` argument, replacing the deprecated ``password``
    argument.

    Args:
        path: Absolute path to the .p8 private key file.

    Returns:
        DER-encoded private key bytes suitable for the Snowflake connector.

    Raises:
        FileNotFoundError: If no file exists at ``path``.
        ValueError: If the file content is not a valid PEM-encoded private key.
    """
    with open(path, "rb") as key_file:
        p_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )
    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
