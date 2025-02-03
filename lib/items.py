import logging
import json
import asyncio
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from optypes.op_types import BaseHandler, Item
from util.utils import AsyncExecutor
from lib.command_builder import CommandBuilder
from lib.base_handler import BaseOpHandler

logger = logging.getLogger(__name__)

class ItemNotFoundError(Exception):
    """Raised when an item cannot be found"""
    pass

class ItemOperationError(Exception):
    """Raised when an item operation fails"""
    pass

@dataclass
class ItemSearchResult:
    """Structured result for item searches"""
    item_id: str
    vault_id: str
    title: str
    category: str
    last_edited_by: str
    created_at: str
    
class ItemHandler(BaseOpHandler):
    """Handles operations related to 1Password items"""

    def __init__(self):
        super().__init__(resource_type="item")

    async def list(self, vault_id: Optional[str] = None) -> List[Item]:
        """List items, optionally filtered by vault"""
        try:
            items_json = await self._execute(
                subcommand="list",
                options={"vault": vault_id}
            )
            return [Item(**item) for item in items_json]
        except Exception as e:
            logger.error(f"Failed to list items: {str(e)}")
            raise ItemOperationError("Failed to retrieve items list") from e

    async def get(self, item_id: str) -> Item:
        """Get details for a specific item"""
        try:
            item_json = await self._execute(
                subcommand="get",
                args=[item_id]
            )
            return Item(**item_json)
        except Exception as e:
            if "not found" in str(e).lower():
                raise ItemNotFoundError(f"Item {item_id} not found")
            logger.error(f"Failed to get item {item_id}: {str(e)}")
            raise ItemOperationError(f"Failed to retrieve item {item_id}") from e

    async def list_with_details(
        self, 
        vault_id: Optional[str] = None,
        chunk_size: int = 10
    ) -> List[Item]:
        """List items with full details, handling pagination
        
        Args:
            vault_id: Optional vault ID to filter items
            chunk_size: Number of items to process concurrently
            
        Returns:
            List of Item objects with full details
        """
        items = await self.list(vault_id)
        
        if not items:
            return []

        chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
        
        detailed_items: List[Item] = []
        for chunk in chunks:
            tasks = [self.get(item.id) for item in chunk]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Failed to get item details: {result}")
                    continue
                detailed_items.append(result)

        return detailed_items

    async def list_and_get_items(self, vault_id: Optional[str] = None) -> List[Item]:
        """Get a list of items with full details"""
        try:
            return await self.list_with_details(vault_id)
        except Exception as e:
            logger.error(f"Failed to list and get items: {str(e)}")
            raise ItemOperationError("Failed to retrieve detailed items list") from e
