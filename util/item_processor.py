import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from lib.items import ItemHandler
from optypes.op_types import ItemField
from lib.base_handler import BaseOpHandler

from util.utils import AsyncExecutor

class ItemProcessor(BaseOpHandler):
    # maybe this class hsould be renamed to ItemSearcher or something.
    def __init__(self, max_workers: int = 8):
        super().__init__(resource_type="item")
        self.items = ItemHandler()
        self.max_workers = max_workers
        self.executor = AsyncExecutor()

    async def process_item_chunks(self, item_chunks, search_term):
        logging.info(
            f"Processing {len(item_chunks)} chunks of items for search term: {search_term}"
        )

        results = []

        chunk_results = await self.executor.execute(
            tasks=item_chunks,
            task_func=self._process_item_chunk,
            search_term=search_term,
        )

        for result in chunk_results:
            if result:
                results.extend(result)

        logging.info(
            f"All item chunks have been processed for search term: {search_term}"
        )
        return results

    async def _process_item_chunk(self, item_chunks, search_term):
        logging.info(
            f"Starting processing for chunk of {len(item_chunks)} items."
        )

        start_time = time.perf_counter()
        results = []

        for item_set in item_chunks:
            for item in item_set:

                try:
                    get_item = await self.items.get(item.id)
                    match = self._extract_search_term(search_term, get_item)
                    if match:
                        results.append(match)
                except Exception as e:
                    logging.error(f"Error processing item {item}: {e}")
                    continue

        elapsed_time = time.perf_counter() - start_time
        logging.info(
            f"Processed chunk of {len(item_chunks)} items in {elapsed_time:.2f} seconds."
        )

        return results

    def _extract_search_term(self, search_term: str, item):
        for field in item.fields:
            field_dict = field.dict(exclude_none=True)
            for attr, value in field_dict.items():
                if isinstance(value, str) and search_term in value:
                    return item
        return None
