from __future__ import annotations

from opportunity_crawler.collection.adapters.base import BaseAdapter


class ApiOrFeedAdapter(BaseAdapter):
    mode = "api_or_feed"

