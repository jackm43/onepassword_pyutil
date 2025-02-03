import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from optypes.op_types import (
    BaseHandler,
    PermissionOperator,
    UserDetails,
    VaultDetails,
    VaultOverview,
    VaultPermissionUpdate,
    VaultUserPermissionUpdate,
)
from util.utils import AsyncExecutor
from lib.base_handler import BaseOpHandler

logger = logging.getLogger(__name__)

class VaultPermissionError(Exception):
    """Raised when vault permission operations fail"""
    pass

class VaultOperationError(Exception):
    """Raised when vault operations fail"""
    pass

class PermissionAction(Enum):
    GRANT = "grant"
    REVOKE = "revoke"

# TODO: This probs need to be adapted better for similar styling to items/users/groups
@dataclass
class VaultPermission:
    permission_name: str
    allowed: bool

class VaultHandler(BaseOpHandler):
    """
    Access these functions like VaultHandler.group.get or VaultHandler.list.
    The former is used when the command(group) has a subcommand (group).
    """

    def __init__(self):
        super().__init__(resource_type="vault")
        self.executor = AsyncExecutor()
        self.group = self.Group(parent_handler=self)
        self.user = self.User(parent_handler=self)
        self.vaults = self

    async def list(self, permissions: Optional[str] = None) -> List[VaultOverview]:
        """List vaults, optionally filtered by permissions"""
        try:
            options = {"permissions": permissions} if permissions else None
            vaults_json = await self._execute(
                subcommand="list",
                options=options
            )
            return [VaultOverview(**vault) for vault in vaults_json]
        except Exception as e:
            logger.error(f"Failed to list vaults: {str(e)}")
            raise VaultOperationError("Failed to retrieve vaults list") from e

    async def get(self, vault_id: str) -> VaultDetails:
        """Get detailed information about a specific vault
        
        Args:
            vault_id: The ID or name of the vault
            
        Returns:
            VaultDetails object containing vault information
            
        Raises:
            VaultPermissionError: If user lacks permission to access the vault
        """
        try:
            cmd = f"vault get {vault_id}"
            vault_json = await self.client.run_command_async(cmd)
            return VaultDetails(**vault_json)
        except Exception as e:
            logger.error(f"Failed to get vault {vault_id}: {str(e)}")
            raise VaultPermissionError(f"Unable to access vault {vault_id}") from e

    async def update_permissions(
        self,
        vault_id: str,
        user_id: str,
        action: PermissionAction,
        permissions: List[str]
    ) -> VaultPermissionUpdate:
        """Update permissions for a user on a vault
        
        Args:
            vault_id: The ID of the vault
            user_id: The ID of the user
            action: PermissionAction.GRANT or PermissionAction.REVOKE
            permissions: List of permission names to update
            
        Returns:
            VaultPermissionUpdate containing the result of the operation
        """
        cmd = (
            f"vault user {action.value} {vault_id} {user_id} "
            f"--permissions {','.join(permissions)}"
        )
        
        try:
            result = await self.client.run_command_async(cmd)
            return VaultPermissionUpdate(**result)
        except Exception as e:
            logger.error(
                f"Failed to {action.value} permissions for user {user_id} "
                f"on vault {vault_id}: {str(e)}"
            )
            raise VaultPermissionError(
                f"Permission update failed for vault {vault_id}"
            ) from e

    async def _handle_vault_users_list(self, vault: str) -> List[UserDetails]:
        """Lists users in a vault and ensures return type is List[UserDetails]."""
        cmd = f"vault user list {vault}"

        try:
            vault_users_json = await self.client.run_command_async(cmd)
            vault_users = [UserDetails(**vault) for vault in vault_users_json]
            return vault_users
        except (TypeError, KeyError) as e:
            logging.error(f"Failed to parse result into UserDetails: {e}")
            raise ValueError(f"Invalid response structure: {vault_users_json}")

    async def handle_vault_group_permission(
        self, action: PermissionOperator, vault_id: str, permission: str, group: str
    ) -> VaultPermissionUpdate:
        """Handle vault group permission updates"""
        try:
            cmd = f"vault group {action.value} {vault_id} {group} --permissions {permission}"
            result = await self.client.run_command_async(cmd)
            return VaultPermissionUpdate(**result)
        except Exception as e:
            logger.error(f"Failed to {action.value} group permission: {e}")
            raise VaultPermissionError(f"Failed to {action.value} group permission") from e

    async def handle_vault_user_permission(
        self, action: PermissionOperator, vault_id: str, users: List[UserDetails], permissions: str
    ) -> List[VaultUserPermissionUpdate]:
        """Handle vault user permission updates"""
        try:
            results = []
            for user in users:
                cmd = f"vault user {action.value} {vault_id} {user.id} --permissions {permissions}"
                result = await self.client.run_command_async(cmd)
                results.append(VaultUserPermissionUpdate(**result))
            return results
        except Exception as e:
            logger.error(f"Failed to {action.value} user permission: {e}")
            raise VaultPermissionError(f"Failed to {action.value} user permission") from e

    class Group:
        def __init__(self, parent_handler):
            self.parent_handler = parent_handler

        async def revoke(
            self, vault_id: str, permission: str, group: str
        ) -> VaultPermissionUpdate:

            return await self.parent_handler.handle_vault_group_permission(
                PermissionOperator.REVOKE, vault_id, permission, group
            )

        async def grant(
            self, vault_id: str, permission: str, group: str
        ) -> VaultPermissionUpdate:

            return await self.parent_handler.handle_vault_group_permission(
                PermissionOperator.GRANT, vault_id, permission, group
            )

    class User:
        def __init__(self, parent_handler):
            self.parent_handler = parent_handler

        async def revoke(
            self, user_ids: List[UserDetails], vault_id: str, permissions: str
        ) -> List[VaultUserPermissionUpdate]:

            return await self.parent_handler.handle_vault_user_permission(
                PermissionOperator.REVOKE, vault_id, user_ids, permissions
            )

        async def grant(
            self, user_ids: List[UserDetails], vault_id: str, permissions: str
        ) -> List[VaultUserPermissionUpdate]:

            return await self.parent_handler.handle_vault_user_permission(
                PermissionOperator.GRANT, vault_id, user_ids, permissions
            )

        async def list(self, vault: str) -> List[UserDetails]:
            """List users in a vault"""
            return await self.parent_handler._handle_vault_users_list(vault)
