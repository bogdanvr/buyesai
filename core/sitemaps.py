# project/sitemaps.py
from django.urls import reverse
from django.contrib.sitemaps import Sitemap

class StaticViewSitemap(Sitemap):
    changefreq = "weekly"
    priority = 1.0

    def items(self):
        return ["/"]  # главная

    def location(self, item):
        return item
