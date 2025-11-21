"""FitBit OAuth2 authorization helper utilities."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import structlog
from requests_oauth2client import BearerToken, OAuth2Client

__all__ = [
    "FITBIT_AUTHORIZATION_ENDPOINT",
    "FITBIT_REVOCATION_ENDPOINT",
    "FITBIT_TOKEN_ENDPOINT",
    "REQUIRED_SCOPES",
    "create_fitbit_client",
    "get_env_or_exit",
    "main",
]

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ]
)
logger = structlog.get_logger()

# FitBit OAuth2 endpoints
FITBIT_AUTHORIZATION_ENDPOINT = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_ENDPOINT = "https://api.fitbit.com/oauth2/token"
FITBIT_REVOCATION_ENDPOINT = "https://api.fitbit.com/oauth2/revoke"

# Activity to get all the recorded activities, location to get the GPS data from the
# activities and profile for basic user info
REQUIRED_SCOPES = ["activity", "location", "profile"]


def get_env_or_exit(var_name: str) -> str:
    """Get environment variable or exit with error message.

    Args:
        var_name: The name of the environment variable to retrieve.

    Returns:
        The value of the environment variable.

    Raises:
        SystemExit: If the environment variable is not set.
    """
    value = os.environ.get(var_name)
    if not value:
        logger.error(
            "Environment variable not set",
            variable=var_name,
            help=f"Please set {var_name} environment variable",
        )
        sys.exit(1)
    return value


def create_fitbit_client(
    client_id: str, client_secret: str, redirect_uri: str
) -> OAuth2Client:
    """Create an OAuth2 client configured for FitBit API.

    Args:
        client_id: The FitBit application client ID.
        client_secret: The FitBit application client secret.
        redirect_uri: The redirect URI configured in the FitBit application.

    Returns:
        An configured OAuth2Client instance.
    """
    logger.info(
        "Creating FitBit OAuth2 client",
        authorization_endpoint=FITBIT_AUTHORIZATION_ENDPOINT,
        token_endpoint=FITBIT_TOKEN_ENDPOINT,
    )

    return OAuth2Client(
        authorization_endpoint=FITBIT_AUTHORIZATION_ENDPOINT,
        token_endpoint=FITBIT_TOKEN_ENDPOINT,
        revocation_endpoint=FITBIT_REVOCATION_ENDPOINT,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        code_challenge_method="S256",  # PKCE with SHA-256
    )


def _write_token_to_file(token: BearerToken, output_path: Path) -> None:
    """Persist the retrieved token data to disk."""
    token_data = {
        "access_token": token.access_token,
        "refresh_token": token.refresh_token,
        "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        "scope": token.scope,
        "token_type": token.token_type,
        "id_token": str(token.id_token) if token.id_token else None,
    }

    if getattr(token, "kwargs", None):
        token_data.update(token.kwargs)

    output_path = output_path.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as token_file:
        json.dump(token_data, token_file, indent=2)
        token_file.write("\n")

    logger.info("Saved token response to disk", path=str(output_path))


def main() -> None:
    """Run the FitBit OAuth2 authorization flow tool"""
    logger.info("Starting FitBit OAuth2 Flow Helper")

    # Get credentials from environment
    client_id = get_env_or_exit("FB_CLIENT_ID")
    client_secret = get_env_or_exit("FB_CLIENT_SECRET")

    # FitBit requires a HTTPS endpoint. Setting up a local HTTPS server is out of scope so
    #    we do not attempt to start a web server and just ask the user to copy/paste the
    #    redirect URL.
    redirect_uri = "https://localhost:8080/callback"

    logger.info(
        "Using configuration",
        client_id=client_id[:8] + "...",
        redirect_uri=redirect_uri,
        scopes=REQUIRED_SCOPES,
    )

    # Create OAuth2 client
    client = create_fitbit_client(client_id, client_secret, redirect_uri)

    # Generate authorization request
    logger.info("Generating authorization request")
    auth_request = client.authorization_request(
        scope=REQUIRED_SCOPES,
        # FitBit requires response_type=code for authorization code flow
        response_type="code",
    )

    # Display the authorization URL
    print("\n" + "=" * 80)
    print("STEP 1: Visit the following URL to authorize the application:")
    print("=" * 80)
    print(f"\n{auth_request.uri}\n")
    print("=" * 80)

    # Get the callback URL from the user
    print(
        "\nSTEP 2: After authorizing, you'll be redirected to a URL which may display an error in the browser."
    )
    print("Copy the entire URL from your browser and paste it here.")
    callback_url = input("\nPaste the callback URL here: ").strip()

    if not callback_url:
        logger.error("No callback URL provided")
        sys.exit(1)

    # Parse the callback URL to extract the authorization code
    logger.info("Parsing callback URL")
    try:
        parsed_url = urlparse(callback_url)
        query_params = parse_qs(parsed_url.query)

        # Check for error response
        if "error" in query_params:
            error = query_params["error"][0]
            error_description = query_params.get(
                "error_description", ["Unknown error"]
            )[0]
            logger.error(
                "Authorization failed",
                error=error,
                description=error_description,
            )
            sys.exit(1)

        # Extract authorization code
        if "code" not in query_params:
            logger.error("No authorization code found in callback URL")
            sys.exit(1)

        auth_code = query_params["code"][0]
        logger.info("Authorization code received", code=auth_code[:10] + "...")

    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Failed to parse callback URL", error=str(exc))
        sys.exit(1)

    # Exchange authorization code for access token
    logger.info("Exchanging authorization code for access token")
    logger.debug(
        "Exchanging code",
        code=auth_code,
        redirect_uri=redirect_uri,
        verify=auth_request.code_verifier,
    )
    try:
        token = client.authorization_code(
            code=auth_code,
            # Pass the code verifier for PKCE
            code_verifier=auth_request.code_verifier,
            redirect_uri=redirect_uri,
        )

        logger.info(
            "Access token received successfully",
            token_type=token.token_type,
            expires_in=token.expires_in,
            scope=token.scope,
        )

        # Display the token information
        print("\n" + "=" * 80)
        print("SUCCESS! Access token received:")
        print("=" * 80)
        print(f"\nAccess Token: {token.access_token}")
        print(f"Token Type: {token.token_type}")
        print(f"Expires In: {token.expires_in} seconds")
        print(f"Scope: {token.scope}")
        if token.refresh_token:
            print(f"Refresh Token: {token.refresh_token}")
        print("\n" + "=" * 80)

        logger.info("Credential Helper completed successfully")

        output_file = Path(os.environ.get("FB_CLIENT_SECRET_FILE", "tokens.json"))
        try:
            _write_token_to_file(token, output_file)
        except OSError as exc:
            logger.error(
                "Failed to write token file",
                path=str(output_file),
                error=str(exc),
            )
            sys.exit(1)

    except Exception as exc:  # pragma: no cover - external dependency failure
        logger.error("Failed to exchange authorization code", error=exc)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
