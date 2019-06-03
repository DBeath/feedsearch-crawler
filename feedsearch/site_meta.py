# from typing import Any
#
# from crawler.item import Item
# from crawler.response import Response
# from yarl import URL
#
#
# class SiteMeta(Item):
#     url: URL = None
#     site_url: str = ""
#     site_name: str = ""
#     icon_url: URL = ""
#     icon_data_uri: str = ""
#
#     def __init__(self, url: URL) -> None:
#         super().__init__()
#         self.url = url
#
#     async def parse_site_info_async(
#         self, soup, response: Response, favicon_data_uri: bool = False
#     ):
#         """
#         Finds Site Info from root domain of site
#
#         :return: None
#         """
#         self.url = self.find_site_url(soup)
#         self.site_name = self.find_site_name(soup)
#         self.icon_url = await self.find_site_icon_url_async(soup, self.url)
#
#         if favicon_data_uri and self.icon_url:
#             self.icon_data_uri = await self.create_data_uri_async(self.icon_url)
#
#     async def find_site_icon_url_async(self, soup, url: URL) -> URL:
#         """
#         Attempts to find Site Favicon
#
#         :param url: Root domain Url of Site
#         :return: str
#         """
#         icon_rel = ["apple-touch-icon", "shortcut icon", "icon"]
#
#         icon = ""
#         for rel in icon_rel:
#             link = soup.find(name="link", rel=rel)
#             if link:
#                 icon = link.get("href", None)
#                 if icon[0] == "/":
#                     icon = "{0}{1}".format(url, icon)
#                 if icon == "favicon.ico":
#                     icon = "{0}/{1}".format(url, icon)
#         if not icon:
#             send_url = url.join(URL("/favicon.ico"))
#             self.logger.debug("Trying url %s for favicon", send_url)
#             request =
#             response = await get_url_async(send_url, get_timeout(), get_exceptions())
#             if response and response.status_code == 200:
#                 logger.debug("Received url %s for favicon", response.url)
#                 icon = response.url
#         return icon
#
#     @staticmethod
#     def find_site_name(soup) -> str:
#         """
#         Attempts to find Site Name
#
#         :param soup: BeautifulSoup of site
#         :return: str
#         """
#         site_name_meta = [
#             "og:site_name",
#             "og:title",
#             "application:name",
#             "twitter:app:name:iphone",
#         ]
#
#         for p in site_name_meta:
#             try:
#                 name = soup.find(name="meta", property=p).get("content")
#                 if name:
#                     return name
#             except AttributeError:
#                 pass
#
#         try:
#             title = soup.find(name="title").text
#             if title:
#                 return title
#         except AttributeError:
#             pass
#
#         return ""
#
#     @staticmethod
#     def find_site_url(soup, url: URL) -> URL:
#         """
#         Attempts to find the canonical Url of the Site
#
#         :param soup: BeautifulSoup of site
#         :param url: Current Url of site
#         :return: str
#         """
#         canonical = soup.find(name="link", rel="canonical")
#         try:
#             site = canonical.get("href")
#             if site:
#                 return URL(site)
#         except AttributeError:
#             pass
#
#         meta = soup.find(name="meta", property="og:url")
#         try:
#             site = meta.get("content")
#         except AttributeError:
#             return url
#         return URL(site)
