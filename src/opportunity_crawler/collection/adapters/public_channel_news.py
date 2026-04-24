from __future__ import annotations

from opportunity_crawler.collection.adapters.public_search_list_detail import PublicSearchListDetailAdapter


class PublicChannelNewsAdapter(PublicSearchListDetailAdapter):
    mode = "public_channel_news"

