import logging
from dataclasses import fields
from typing import Any, Awaitable, Callable, Dict, Optional

from optypes.op_types import PermissionOperator, Permissions, TestingItems
from util.utils import async_input, run_async

from .actions import Actions


class RouterError(Exception):
    """Base exception for router errors"""
    pass

class InvalidActionError(RouterError):
    """Raised when an invalid action is requested"""
    pass

class InvalidPermissionError(RouterError):
    """Raised when invalid permissions are provided"""
    pass

class Router:
    ACTION_OPERATORS = {
        "grant": PermissionOperator.GRANT,
        "revoke": PermissionOperator.REVOKE,
    }

    AVAILABLE_ACTIONS = {
        "IR-CredSearch-AllVaults": {
            "help": "Search for credentials in all vaults",
            "run": "run_ir_cred_search_all_vaults",
        },
        "IR-CredSearch-SingleVault": {
            "help": "Search for credentials in a single vault",
            "run": "run_ir_cred_search_single_vault",
        },
        "IR-CredSearch-Complete": {
            "help": "Once you're done searching, run this to clean up permissions.",
            "run": "run_ir_complete",
        },
        "Modify-User-Permissions": {
            "help": "Grant or revoke permissions for vault users",
            "run": "run_user_permission_update",
        },
    }

    def __init__(self, testing: bool = False) -> None:
        self.testing = testing
        self.actions = Actions(testing)
        self.permission_opts = [
            Permissions.ALLOW_VIEWING,
            Permissions.EXPORT_ITEMS,
            *[getattr(Permissions, field.name) for field in fields(Permissions)]
        ]

    def post_init_checks(self, testing: bool):
        self.actions = Actions(testing)

    def run_action(self, action: str) -> Any:
        """
        Executes the specified action.

        Args:
            action (str): The action key to execute.

        Returns:
            Any: The result of the action.
        """
        if action not in self.AVAILABLE_ACTIONS:
            logging.error(f"Action '{action}' not found.")
            raise ValueError(f"Action '{action}' not found.")

        assert (
            self.actions is not None
        ), "Make sure post_init_checks is being run"

        run_coro: Callable[[], Awaitable[Any]] = getattr(self, self.AVAILABLE_ACTIONS[action]["run"])

        logging.info(f"Executing action: {action}")
        return run_async(run_coro())

    def get_help_text(self) -> str:
        """
        Generates help text for all available actions.

        Returns:
            str: The help text string.
        """
        return "\n".join(
            [
                f"{i + 1}. {action.ljust(25)} - {details['help']}"
                for i, (action, details) in enumerate(self.AVAILABLE_ACTIONS.items())
            ]
        )

    async def run_ir_cred_search_all_vaults(self) -> Any:
        if not self.testing:
            search_term = await async_input("Enter search term: ")
        else:
            search_term = TestingItems.SEARCH_TERM

        results = await self.actions.ir_credential_search(search_term)

        return results

    async def validate_vault_id(self, vault_id: str) -> bool:
        """Validate vault ID exists"""
        try:
            await self.actions.vaults.get(vault_id)
            return True
        except Exception:
            raise RouterError(f"Invalid vault ID: {vault_id}")

    async def run_ir_cred_search_single_vault(self) -> Any:
        if not self.testing:
            search_term = await async_input("Enter search term: ")
            vault_id = await async_input("Enter vault ID: ")
            await self.validate_vault_id(vault_id)
        else:
            search_term = TestingItems.SEARCH_TERM
            vault_id = TestingItems.TEST_VAULT_ID

        results = await self.actions.ir_credential_search(
            search_term, vault_id
        )

        return results

    async def run_ir_complete(self) -> Any:
        return await self.actions.ir_complete()

    async def run_user_permission_update(self) -> Any:
        try:
            if not self.testing:
                vault_id = await async_input("Enter vault ID: ")
                action_input = await async_input(
                    f"What action would you like to take?\n {list(self.ACTION_OPERATORS.values())}\n\n"
                )

                if action_input not in self.ACTION_OPERATORS.values():
                    raise InvalidActionError(f"Invalid action: {action_input}")

                permissions_input = await async_input(
                    f"Provide a comma separated list of permissions you want to take action on: \n{self.permission_opts}\n\n"
                )
                permissions = [
                    permission.strip()
                    for permission in permissions_input.split(",")
                ]
                invalid_permissions = [
                    perm
                    for perm in permissions
                    if perm not in self.permission_opts
                ]

                if invalid_permissions:
                    raise InvalidPermissionError(
                        f"Invalid permissions provided: {', '.join(invalid_permissions)}"
                    )

                action = self.ACTION_OPERATORS[action_input]

            else:
                vault_id = TestingItems.TEST_VAULT_ID
                action_input = await async_input("Enter (grant/revoke): \n\n")
                action = self.ACTION_OPERATORS[action_input]
                permissions = [Permissions.EXPORT_ITEMS]

            return await self.actions.update_user_permission(
                vault_id=vault_id, action=action, permissions=permissions
            )
        except (InvalidActionError, InvalidPermissionError) as e:
            self.logger.error(str(e))
            raise
