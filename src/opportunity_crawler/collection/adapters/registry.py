from __future__ import annotations

from opportunity_crawler.collection.adapters.api_or_feed import ApiOrFeedAdapter
from opportunity_crawler.collection.adapters.attachment_document import AttachmentDocumentAdapter
from opportunity_crawler.collection.adapters.base import BaseAdapter
from opportunity_crawler.collection.adapters.login_search_list_detail import LoginSearchListDetailAdapter
from opportunity_crawler.collection.adapters.manual_import import ManualImportAdapter
from opportunity_crawler.collection.adapters.public_channel_news import PublicChannelNewsAdapter
from opportunity_crawler.collection.adapters.public_search_list_detail import PublicSearchListDetailAdapter
from opportunity_crawler.collection.adapters.spa_or_ajax_search import SpaOrAjaxSearchAdapter


class AdapterRegistry:
    def __init__(self, adapters: list[BaseAdapter]) -> None:
        self._adapters = {adapter.mode: adapter for adapter in adapters}

    @classmethod
    def default(cls) -> "AdapterRegistry":
        return cls(
            [
                PublicSearchListDetailAdapter(),
                PublicChannelNewsAdapter(),
                LoginSearchListDetailAdapter(),
                SpaOrAjaxSearchAdapter(),
                AttachmentDocumentAdapter(),
                ApiOrFeedAdapter(),
                ManualImportAdapter(),
            ]
        )

    def resolve(self, mode: str) -> BaseAdapter:
        try:
            return self._adapters[mode]
        except KeyError as exc:
            raise KeyError(f"unsupported adapter mode: {mode}") from exc

