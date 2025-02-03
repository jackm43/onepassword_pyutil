import logging
from typing import List, Optional
from dataclasses import dataclass

from optypes.op_types import (
    GroupSet,
    PermissionOperator,
    Permissions,
    TestingItems,
    UserDetails,
    VaultOverview,
)
from util.item_processor import ItemProcessor
from util.utils import chunk_list
from util.vault_perm_manager import VaultPermissionsManager

from lib.items import ItemHandler, ItemOperationError
from lib.users import UserHandler, UserOperationError
from lib.vaults import VaultHandler

logger = logging.getLogger(__name__)

class ActionError(Exception):
    """Base exception for action-level errors"""
    pass

class SearchError(ActionError):
    """Raised when search operations fail"""
    pass

class PermissionError(ActionError):
    """Raised when permission operations fail"""
    pass

class Actions:
    def __init__(self, testing: bool = False) -> None:
        self.vaults = VaultHandler()
        self.users = UserHandler()
        self.items = ItemHandler()
        self.testing = testing

        self.permissions_manager = VaultPermissionsManager()
        self.item_processor = ItemProcessor()

    async def ir_credential_search(
        self, search_term: str, vault_id: Optional[str] = None
    ) -> List[dict]:
        """Search for credentials in specified vault or all vaults
        
        Args:
            search_term: Term to search for
            vault_id: Optional vault to search in
            
        Returns:
            List of matching credentials
            
        Raises:
            SearchError: If search operation fails
        """
        try:
            if self.testing:
                return await self._handle_vault_search(
                    search_term=TestingItems.SEARCH_TERM,
                    vault_id=TestingItems.TEST_VAULT_ID,
                )
            return await self._handle_vault_search(search_term, vault_id)
        except (ItemOperationError, UserOperationError) as e:
            logger.error(f"Failed during credential search: {e}")
            raise SearchError(f"Credential search failed: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            raise SearchError("Unexpected error during credential search") from e

    async def ir_complete(self) -> None:
        """Revoke permissions for all vaults
        
        Raises:
            PermissionError: If permission revocation fails
        """
        try:
            vaults = await self.vaults.list(permissions=Permissions.ALLOW_VIEWING)
            vault_chunks = chunk_list(vaults, 10)
            logger.info(f"Processing {len(vault_chunks)} chunks of vaults")

            await self.permissions_manager.update_permissions_for_vaults(
                vault_chunks,
                group=GroupSet.OWNERS,
                permission=Permissions.ALLOW_VIEWING,
                action=PermissionOperator.REVOKE,
            )
            logger.info("Successfully revoked all vault permissions")
        except Exception as e:
            logger.error(f"Failed to complete IR process: {e}")
            raise PermissionError(f"Failed to revoke permissions: {str(e)}") from e

    async def update_user_permission(
        self,
        action: PermissionOperator,
        permissions: List[str],
        vault_id: Optional[str] = None,
    ) -> None:
        """Grant or revoke user permissions for vaults."""
        try:
            joined_permissions = ",".join(permissions)
            vaults = []
            if self.testing:
                vaults = [
                    VaultOverview(
                        id=TestingItems.TEST_VAULT_ID,
                        name="Security",
                    )
                ]
            elif vault_id:
                vault_details = await self.vaults.get(vault_id)
                vault = VaultOverview(id=vault_details.id, name=vault_details.name)
                vaults = [vault]
            else:
                vaults = await self.vaults.list(permissions=joined_permissions)

            for vault in vaults:
                vault_user_list = await self.vaults.user.list(vault=vault.id)
                filtered_users = await self._filter_users_by_permission(
                    vault_user_list, permissions, action
                )

                users_in_vault_chunks = chunk_list(filtered_users, 100)
                await self.permissions_manager.update_permissions_for_user(
                    users_in_vault_chunks,
                    permissions=joined_permissions,
                    action=action,
                    vault_id=vault.id,
                )
        except Exception as e:
            logger.error(f"Failed to update user permissions: {e}")
            raise

    async def _filter_users_by_permission(
        self,
        vault_user_list: List[UserDetails],
        permissions: List[str],
        action: PermissionOperator,
    ) -> List[UserDetails]:
        """Filters the user list based on their current permissions."""
        filtered_users = []
        for vault_user in vault_user_list:
            for permission in permissions:
                if (
                    action == PermissionOperator.REVOKE
                    and permission in vault_user.permissions
                ):
                    filtered_users.append(vault_user)
                elif (
                    action == PermissionOperator.GRANT
                    and permission not in vault_user.permissions
                ):
                    filtered_users.append(vault_user)
        return filtered_users

    async def _handle_vault_search(
        self, search_term: str, vault_id: Optional[str] = None
    ) -> List[dict]:
        """
        Handles the process of searching items across vaults.
        """
        try:
            if self.testing:
                vaults = [
                    VaultOverview(
                        id=TestingItems.TEST_VAULT_ID,
                        name="Security",
                    )
                ]
            else:
                if vault_id:
                    vault = await self.vaults.get(vault_id)
                    vaults = [VaultOverview(id=vault.id, name=vault.name)]
                else:
                    vaults = await self.vaults.list()

            vault_chunks = chunk_list(vaults, 10)

            await self.permissions_manager.update_permissions_for_vaults(
                vault_chunks,
                group=GroupSet.OWNERS,
                permission=Permissions.ALLOW_VIEWING,
                action=PermissionOperator.GRANT,
            )

            all_items = await self.items.list(vault_id)
            item_chunks = chunk_list(all_items, 10)

            if self.testing:
                item_chunks = [item_chunks[:1]]  # Process only the first chunk in testing

            results = await self.item_processor.process_item_chunks(
                item_chunks, search_term
            )
            return results
        except Exception as e:
            logger.error(f"Failed to handle vault search: {e}")
            raise
