import logging
from yarl import URL
from crawler.response import Response
from crawler.request import Request
from feedsearch.site_meta import SiteMeta


class SiteMetaProcessor:
    def __init__(self, spider):
        self.spider = spider
        self.logger = logging.getLogger(__name__)

    async def process(self, url: URL, request: Request, response: Response) -> SiteMeta:
        site_meta = SiteMeta(url)

        site_meta.url = self.find_site_url(response.parsed_xml, url)
        site_meta.site_name = self.find_site_name(response.parsed_xml)
        site_meta.icon_url = self.find_site_icon_url(response.parsed_xml, url)

        return site_meta

    def find_site_icon_url(self, soup, url) -> URL:
        icon_rel = ["apple-touch-icon", "shortcut icon", "icon"]

        for rel in icon_rel:
            link = soup.find(name="link", rel=rel)
            if link:
                icon = link.get("href", None)
                return url.join(URL(icon))
        return URL()

    @staticmethod
    def find_site_url(soup, url: URL) -> URL:
        """
        Attempts to find the canonical Url of the Site

        :param soup: BeautifulSoup of site
        :param url: Current Url of site
        :return: str
        """
        canonical = soup.find(name="link", rel="canonical")
        try:
            site = canonical.get("href")
            if site:
                return URL(site)
        except AttributeError:
            pass

        meta = soup.find(name="meta", property="og:url")
        try:
            site = meta.get("content")
        except AttributeError:
            return url
        return URL(site)

    @staticmethod
    def find_site_name(soup) -> str:
        """
        Attempts to find Site Name

        :param soup: BeautifulSoup of site
        :return: str
        """
        site_name_meta = [
            "og:site_name",
            "og:title",
            "application:name",
            "twitter:app:name:iphone",
        ]

        for p in site_name_meta:
            try:
                name = soup.find(name="meta", property=p).get("content")
                if name:
                    return name
            except AttributeError:
                pass

        try:
            title = soup.find(name="title").text
            if title:
                return title
        except AttributeError:
            pass

        return ""
