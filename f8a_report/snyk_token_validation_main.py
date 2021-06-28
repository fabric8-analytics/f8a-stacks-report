"""Snyk Token Validation."""

from f8a_report.helpers.db_gateway import TokenValidationQueries
from f8a_utils.user_token_utils import decrypt_api_token, is_snyk_token_valid
import logging
import json
import os

logger = logging.getLogger(__file__)
DB_CACHE_FILE_PATH = os.environ.get("DB_CACHE_DIR")


def main():
    """Snyk Token Validation."""
    user_to_tokens = TokenValidationQueries().get_registered_user_tokens()
    unregistered_users = call_snyk_api(user_to_tokens)
    TokenValidationQueries().update_users_to_unregistered(unregistered_users)
    cache_all_users(TokenValidationQueries().get_all_user())


def call_snyk_api(user_to_tokens: dict) -> list:
    """Snyk API invocation to figure out unregistered users."""
    unregistered_users = list()
    for user_id, token in user_to_tokens.items():
        decrypted_token = decrypt_api_token(token)
        if not is_snyk_token_valid(decrypted_token.decode()):
            logger.info("User id %s has an invalid token", user_id)
            unregistered_users.append(user_id)

    return unregistered_users


def cache_all_users(users: dict):
    """Cache users in PVC."""
    for user in users:
        user_cache = {
            "user_id": user[0], "snyk_api_token": user[1],
            "last_validated_date": user[2], "status": user[3],
            "registered_date": user[4], "created_date": user[5],
            "updated_date": user[6], "user_source": user[7]
        }

        # Create file for each user into PVC having details about user
        with open(DB_CACHE_FILE_PATH + "/" + user[0] + ".json", 'w', encoding='utf-8') as file:
            json.dump(user_cache, file, ensure_ascii=False, indent=4, default=str)


if __name__ == '__main__':
    main()
