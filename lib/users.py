import logging
from typing import List, Optional
from dataclasses import dataclass

from optypes.op_types import UserDetails, UserOverview
from lib.base_handler import BaseOpHandler

logger = logging.getLogger(__name__)

class UserNotFoundError(Exception):
    """Raised when a user cannot be found"""
    pass

class UserOperationError(Exception):
    """Raised when a user operation fails"""
    pass

@dataclass
class UserFilter:
    """Filter options for user listing"""
    vault_id: Optional[str] = None
    group_id: Optional[str] = None

class UserHandler(BaseOpHandler):
    """Handles operations related to 1Password users"""

    def __init__(self):
        super().__init__(resource_type="user")

    async def list(
        self, 
        vault_id: Optional[str] = None, 
        group_id: Optional[str] = None
    ) -> List[UserOverview]:
        """List users, optionally filtered by vault or group"""
        try:
            users_json = await self._execute(
                subcommand="list",
                options={
                    "vault": vault_id,
                    "group": group_id
                }
            )
            return [UserOverview(**user) for user in users_json]
        except Exception as e:
            logger.error(f"Failed to list users: {str(e)}")
            raise UserOperationError("Failed to retrieve users list") from e

    async def get(self, user_id: str) -> UserDetails:
        """Get detailed information about a specific user"""
        try:
            user_json = await self._execute(
                subcommand="get",
                args=[user_id]
            )
            return UserDetails(**user_json)
        except Exception as e:
            if "not found" in str(e).lower():
                raise UserNotFoundError(f"User {user_id} not found")
            logger.error(f"Failed to get user {user_id}: {str(e)}")
            raise UserOperationError(f"Failed to retrieve user {user_id}") from e
