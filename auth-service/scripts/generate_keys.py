#!/usr/bin/env python3
"""Generate RSA key pairs for JWT token signing.

This script generates RSA private and public key pairs that can be used
for signing and verifying JWT tokens in the authentication service.

Usage:
    python generate_keys.py [--key-size 2048] [--output-dir ./keys] [--force]

The script will create:
- private_key.pem: RSA private key for signing tokens
- public_key.pem: RSA public key for verifying tokens

Next steps after running this script:
1. Add the keys directory to .gitignore
2. Set environment variables:
   - JWT_PRIVATE_KEY=<content of private_key.pem>
   - JWT_PUBLIC_KEY=<content of public_key.pem>
3. Ensure proper file permissions (600 for private key)
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_rsa_key_pair(key_size: int = 2048) -> tuple[bytes, bytes]:
    """Generate RSA private and public key pair.

    Args:
        key_size: Size of the RSA key in bits (default: 2048)

    Returns:
        Tuple of (private_key_pem, public_key_pem) as bytes
    """
    logger.info(f"Generating {key_size}-bit RSA key pair...")

    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )

    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Get public key and serialize it
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    logger.info("RSA key pair generated successfully")
    return private_pem, public_pem


def save_keys(
    private_key: bytes, public_key: bytes, output_dir: Path, force: bool = False
) -> None:
    """Save private and public keys to files.

    Args:
        private_key: Private key in PEM format
        public_key: Public key in PEM format
        output_dir: Directory to save keys
        force: Whether to overwrite existing files
    """
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    private_key_path = output_dir / "private_key.pem"
    public_key_path = output_dir / "public_key.pem"

    # Check if files exist and force flag
    if not force:
        if private_key_path.exists() or public_key_path.exists():
            logger.error(
                f"Key files already exist in {output_dir}. Use --force to overwrite."
            )
            sys.exit(1)

    # Save private key
    logger.info(f"Saving private key to {private_key_path}")
    with open(private_key_path, "wb") as f:
        f.write(private_key)

    # Set restrictive permissions on private key (Unix-like systems)
    if os.name != "nt":  # Not Windows
        os.chmod(private_key_path, 0o600)
        logger.info("Set private key permissions to 600")

    # Save public key
    logger.info(f"Saving public key to {public_key_path}")
    with open(public_key_path, "wb") as f:
        f.write(public_key)

    logger.info("Keys saved successfully")


def main() -> None:
    """Main function to generate and save RSA key pairs."""
    parser = argparse.ArgumentParser(
        description="Generate RSA key pairs for JWT token signing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Next steps:
1. Add the keys directory to .gitignore
2. Set environment variables:
   - JWT_PRIVATE_KEY=<content of private_key.pem>
   - JWT_PUBLIC_KEY=<content of public_key.pem>
3. Ensure proper file permissions (600 for private key)
        """,
    )

    parser.add_argument(
        "--key-size",
        type=int,
        default=2048,
        choices=[2048, 3072, 4096],
        help="RSA key size in bits (default: 2048)",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("keys"),
        help="Output directory for key files (default: keys)",
    )

    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing key files"
    )

    args = parser.parse_args()

    try:
        # Generate key pair
        private_key, public_key = generate_rsa_key_pair(args.key_size)

        # Save keys
        save_keys(private_key, public_key, args.output_dir, args.force)

        logger.info("\n" + "=" * 50)
        logger.info("RSA key pair generation completed successfully!")
        logger.info(f"Keys saved to: {args.output_dir.absolute()}")
        logger.info("\nNext steps:")
        logger.info("1. Add the keys directory to .gitignore")
        logger.info("2. Set environment variables:")
        logger.info(
            f"   - JWT_PRIVATE_KEY=<content of {args.output_dir}/private_key.pem>"
        )
        logger.info(
            f"   - JWT_PUBLIC_KEY=<content of {args.output_dir}/public_key.pem>"
        )
        if os.name != "nt":
            logger.info("3. Verify private key permissions are set to 600")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Failed to generate keys: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
