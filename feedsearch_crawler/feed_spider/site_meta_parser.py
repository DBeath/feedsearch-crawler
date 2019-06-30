from yarl import URL

from feedsearch_crawler.crawler import ItemParser, Request, Response
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
        site_meta.site_name = self.find_site_name(xml)
        site_meta.icon_url = self.find_site_icon_url(xml, url)

        if site_meta.icon_url and self.spider.favicon_data_uri:
            yield self.spider.follow(site_meta.icon_url, self.spider.create_data_uri)

        yield site_meta

    @staticmethod
    def find_site_icon_url(soup, url) -> URL:
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
        try:
            canonical = soup.find(name="link", rel="canonical")
            site = canonical.get("href")
            if site:
                return URL(site)
        except AttributeError:
            pass

        try:
            meta = soup.find(name="meta", property="og:url")
            site = meta.get("content")
            if site:
                return URL(site)
        except AttributeError:
            pass

        return url

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
