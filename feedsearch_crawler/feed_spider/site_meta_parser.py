from typing import List

from yarl import URL

from feedsearch_crawler.crawler import ItemParser, Request, Response
from feedsearch_crawler.feed_spider.favicon import Favicon
from feedsearch_crawler.feed_spider.site_meta import SiteMeta


class SiteMetaParser(ItemParser):
    async def parse_item(self, request: Request, response: Response, *args, **kwargs):
        self.logger.info("Parsing: SiteMeta %s", response.url)
        url = response.url
        site_meta: SiteMeta = SiteMeta(url)

        xml = await response.xml
        if not xml:
            return

        site_meta.url = self.find_site_url(xml, url)
        site_meta.host = site_meta.url.host.strip("www.")
        site_meta.site_name = self.find_site_name(xml)
        site_meta.possible_icons = self.find_site_icon_urls(xml, url, site_meta.host)

        for icon in site_meta.possible_icons:
            if icon.url:
                # Only follow favicon urls if we want to create a data uri
                if self.crawler.favicon_data_uri:
                    yield self.follow(
                        icon.url,
                        self.crawler.create_data_uri,
                        cb_kwargs=dict(favicon=icon),
                        allow_domain=True,
                    )
                else:
                    yield icon

        yield site_meta

    @staticmethod
    def find_site_icon_urls(soup, url, host) -> List[Favicon]:
        search_icons = [
            Favicon(
                url=url.join(URL("favicon.ico")), rel="favicon", priority=3, host=host
            ),
            Favicon(url="", rel="shortcut icon", priority=1, host=host),
            Favicon(url="", rel="icon", priority=2, host=host),
        ]

        possible_icons = []
        for icon in search_icons:
            link = soup.find(name="link", rel=icon.rel)
            if link:
                href = link.get("href", None)
                if href:
                    icon.url = url.join(URL(href))
            if icon.url:
                possible_icons.append(icon)

        return sorted(possible_icons, key=lambda x: x.priority)

    @staticmethod
    def find_site_url(soup, url: URL) -> URL:
        """
        Attempts to find the canonical Url of the Site

        :param soup: BeautifulSoup of site
        :param url: Current Url of site
        :return: str
        """
        try:
            canonical = soup.find(name="link", rel="canonical")
            site = canonical.get("href")
            if site:
                return URL(site).origin()
        except AttributeError:
            pass

        try:
            meta = soup.find(name="meta", property="og:url")
            site = meta.get("content")
            if site:
                return URL(site).origin()
        except AttributeError:
            pass

        return url.origin()

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
