from __future__ import annotations

from opportunity_crawler.collection.adapters.public_search_list_detail import PublicSearchListDetailAdapter


class SpaOrAjaxSearchAdapter(PublicSearchListDetailAdapter):
    mode = "spa_or_ajax_search"
