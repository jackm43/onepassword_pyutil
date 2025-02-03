import logging
import time
from typing import Any, List, Optional

from lib.vaults import VaultHandler
from optypes.op_types import PermissionOperator, UserDetails, VaultOverview
from lib.base_handler import BaseOpHandler

from util.utils import AsyncExecutor

class VaultPermissionsManager(BaseOpHandler):
    def __init__(self, max_workers: int = 8):
        super().__init__(resource_type="vault")
        self.executor = AsyncExecutor(max_concurrent_tasks=max_workers)
        self.logger = logging.getLogger(__name__)
        self.vaults = VaultHandler()

    async def update_permissions_for_vaults(
        self,
        vault_chunks: List[List[VaultOverview]],
        group: str,
        permission: str,
        action: PermissionOperator
    ) -> None:
        """Update permissions for chunks of vaults"""
        for chunk in vault_chunks:
            self.logger.info(f"Starting {action.value} permissions for {len(chunk)} vaults.")
            try:
                for vault in chunk:
                    if action == PermissionOperator.GRANT:
                        await self.vaults.group.grant(
                            vault_id=vault.id,
                            permission=permission,
                            group=group
                        )
                    else:
                        await self.vaults.group.revoke(
                            vault_id=vault.id,
                            permission=permission,
                            group=group
                        )
            except Exception as e:
                self.logger.error(f"Error updating permissions for vault {vault.id}: {e}")

    async def update_permissions_for_user(
        self,
        user_chunks: List[List[UserDetails]],
        permissions: str,
        action: PermissionOperator,
        vault_id: str,
    ) -> None:
        self.logger.info(
            f"Processing {len(user_chunks)} chunks of users to {action.value} permissions in vault {vault_id}"
        )

        await self.executor.execute(
            tasks=user_chunks,
            task_func=self.update_user_permission,
            action=action,
            vault_id=vault_id,
            permissions=permissions,
        )

    async def update_group_permission(
        self,
        chunk: List[VaultOverview],
        group: str,
        permission: str,
        action: PermissionOperator,
    ) -> None:
        """Update group permissions for vaults"""
        self.logger.info(f"Starting {action.value} permissions for {len(chunk)} vaults.")
        start_time = time.perf_counter()

        for vault in chunk:
            try:
                if action == PermissionOperator.GRANT:
                    await self.vaults.group.grant(vault.id, permission, group)
                elif action == PermissionOperator.REVOKE:
                    await self.vaults.group.revoke(vault.id, permission, group)
            except Exception as e:
                self.logger.error(
                    f"Error updating permissions for vault {vault.id}: {e}"
                )

        elapsed_time = time.perf_counter() - start_time
        self.logger.info(
            f"Completed {action.value} permissions for {len(chunk)} vaults in {elapsed_time:.2f} seconds."
        )

    async def update_user_permission(
        self,
        chunk: List[UserDetails],
        action: PermissionOperator,
        vault_id: str,
        permissions: Optional[str] = None,
    ) -> None:
        """Update user permissions"""
        self.logger.info(
            f"Running {action.value} for {len(chunk)} users in vault {vault_id} with permissions: {permissions}."
        )

        try:
            if action == PermissionOperator.GRANT:
                await self.vaults.user.grant(chunk, vault_id, permissions)
            elif action == PermissionOperator.REVOKE:
                await self.vaults.user.revoke(chunk, vault_id, permissions)
        except Exception as e:
            self.logger.error(
                f"Error updating permissions for user {chunk} in vault {vault_id}: {e}"
            )
