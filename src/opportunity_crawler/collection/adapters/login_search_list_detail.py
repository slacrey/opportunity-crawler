from __future__ import annotations

from opportunity_crawler.collection.adapters.public_search_list_detail import PublicSearchListDetailAdapter


class LoginSearchListDetailAdapter(PublicSearchListDetailAdapter):
    mode = "login_search_list_detail"

