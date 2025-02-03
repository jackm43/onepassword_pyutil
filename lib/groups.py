import logging
from typing import List, Optional

from optypes.op_types import GroupDetails, GroupOverview
from lib.base_handler import BaseOpHandler

logger = logging.getLogger(__name__)

class GroupOperationError(Exception):
    """Raised when group operations fail"""
    pass

class GroupNotFoundError(GroupOperationError):
    """Raised when a group is not found"""
    pass

class GroupHandler(BaseOpHandler):
    """Handles operations related to 1Password groups"""

    def __init__(self):
        super().__init__(resource_type="group")

    async def list(self) -> List[GroupOverview]:
        """List all groups"""
        try:
            groups_json = await self._execute(subcommand="list")
            return [GroupOverview(**group) for group in groups_json]
        except Exception as e:
            logger.error(f"Failed to list groups: {str(e)}")
            raise GroupOperationError("Failed to retrieve groups list") from e

    async def get(self, group_id: str) -> GroupDetails:
        """Get details for a specific group"""
        try:
            group_json = await self._execute(
                subcommand="get",
                args=[group_id]
            )
            return GroupDetails(**group_json)
        except Exception as e:
            if "not found" in str(e).lower():
                raise GroupNotFoundError(f"Group {group_id} not found")
            logger.error(f"Failed to get group {group_id}: {str(e)}")
            raise GroupOperationError(f"Failed to retrieve group {group_id}") from e

    async def create(self, name: str, description: Optional[str] = None) -> GroupDetails:
        """Create a new group"""
        try:
            options = {"description": description} if description else None
            group_json = await self._execute(
                subcommand="create",
                args=[name],
                options=options
            )
            return GroupDetails(**group_json)
        except Exception as e:
            logger.error(f"Failed to create group {name}: {str(e)}")
            raise GroupOperationError(f"Failed to create group {name}") from e

    async def delete(self, group_id: str) -> None:
        """Delete a group"""
        try:
            await self._execute(
                subcommand="delete",
                args=[group_id]
            )
        except Exception as e:
            if "not found" in str(e).lower():
                raise GroupNotFoundError(f"Group {group_id} not found")
            logger.error(f"Failed to delete group {group_id}: {str(e)}")
            raise GroupOperationError(f"Failed to delete group {group_id}") from e

    async def add_users(self, group_id: str, user_ids: List[str]) -> None:
        """Add users to a group
        
        Args:
            group_id: ID of the group
            user_ids: List of user IDs to add to the group
            
        Raises:
            GroupNotFoundError: If group doesn't exist
            GroupOperationError: If operation fails
        """
        try:
            for user_id in user_ids:
                await self._execute(
                    subcommand="user",
                    args=["add", user_id, group_id]
                )
        except Exception as e:
            if "not found" in str(e).lower():
                raise GroupNotFoundError(f"Group {group_id} not found")
            logger.error(f"Failed to add users to group {group_id}: {str(e)}")
            raise GroupOperationError(f"Failed to add users to group {group_id}") from e

    async def remove_users(self, group_id: str, user_ids: List[str]) -> None:
        """Remove users from a group
        
        Args:
            group_id: ID of the group
            user_ids: List of user IDs to remove from the group
            
        Raises:
            GroupNotFoundError: If group doesn't exist
            GroupOperationError: If operation fails
        """
        try:
            for user_id in user_ids:
                await self._execute(
                    subcommand="user",
                    args=["remove", user_id, group_id]
                )
        except Exception as e:
            if "not found" in str(e).lower():
                raise GroupNotFoundError(f"Group {group_id} not found")
            logger.error(f"Failed to remove users from group {group_id}: {str(e)}")
            raise GroupOperationError(f"Failed to remove users from group {group_id}") from e 