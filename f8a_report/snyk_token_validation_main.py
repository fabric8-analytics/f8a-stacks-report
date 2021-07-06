"""Snyk Token Validation."""

from f8a_report.helpers.db_gateway import TokenValidationQueries
from f8a_utils.user_token_utils import decrypt_api_token, is_snyk_token_valid
import logging
import requests
import tenacity
import os

logger = logging.getLogger(__file__)

_USER_CACHE_API_URL = "http://{host}:{port}/user/refresh_user_cache".format(
    host=os.environ.get("CACHE_SERVICE_HOST", "bayesian-api"),
    port=os.environ.get("CACHE_SERVICE_PORT", "32000"),)
_APP_SECRET_KEY = os.getenv('APP_SECRET_KEY', 'not-set')


def main():
    """Snyk Token Validation."""
    user_to_tokens = TokenValidationQueries().get_registered_user_tokens()
    unregistered_users = call_snyk_api(user_to_tokens)
    TokenValidationQueries().update_users_to_unregistered(unregistered_users)
    cache_all_users()


def call_snyk_api(user_to_tokens: dict) -> list:
    """Snyk API invocation to figure out unregistered users."""
    unregistered_users = list()
    for user_id, token in user_to_tokens.items():
        decrypted_token = decrypt_api_token(token)
        if not is_snyk_token_valid(decrypted_token.decode()):
            logger.info("User id %s has an invalid token", user_id)
            unregistered_users.append(user_id)

    return unregistered_users


@tenacity.retry(reraise=True, stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(1))
def cache_all_users():
    """Cache all users into PVC."""
    logger.info("Invoking API to create user cache.")
    try:
        response = requests.get(_USER_CACHE_API_URL,
                                headers={"APP_SECRET_KEY": _APP_SECRET_KEY})
        logger.info(response.json())
    except Exception as e:
        logger.error(e)


if __name__ == '__main__':
    main()
