#VERSION: 1.2
#AUTHORS: Vikas Yadav (https://github.com/v1k45 | http://v1k45.com)

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the author nor the names of its contributors may be
#      used to endorse or promote products derived from this software without
#      specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function
import re

# python3 suppport (or python2 fallback, if you will)
try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser

from helpers import retrieve_url, download_file
from novaprinter import prettyPrinter


LEETX_DOMAIN = "https://1337x.to"


class LeetxParser(HTMLParser):
    current_result = {}
    current_item = None
    inside_tbody = False
    inside_row = False

    A, TBODY, TR, TD, SPAN = ('a', 'tbody', 'tr', 'td', 'span')

    def handle_starttag(self, tag, attrs):
        # are we inside the results table body or not.
        self.inside_tbody = self.inside_tbody or tag == self.TBODY
        # if not, no need to process this tag any further.
        if not self.inside_tbody:
            return

        # convert attrs tuple to dictonary
        attrs = dict(attrs)

        # for torrent name and link
        link = attrs.get('href', '')
        if self.inside_tbody and tag == self.A and link.startswith('/torrent'):  # noqa
            self.current_result['link'] = LEETX_DOMAIN + link
            self.current_result['desc_link'] = LEETX_DOMAIN + link
            self.current_result['engine_url'] = LEETX_DOMAIN
            self.current_item = 'name'

        # to ignore uploader name attached to the torrent size in span tag
        if tag == self.SPAN:
            self.current_item = None

        # if this is a <td> there can be seeds, leeches or size inside it.
        if tag == self.TD:
            self.inside_row = True

            # find apporipate data key using class name of td
            for item in ['seeds', 'leeches', 'size']:
                if item in attrs.get('class', ''):
                    self.current_item = item
                    break

    def handle_data(self, data):
        # do not process data if we are not inside the table body
        if self.inside_tbody and self.current_item:
            prev_value = self.current_result.get(self.current_item, '')
            self.current_result[self.current_item] = prev_value + data

    def handle_endtag(self, tag):
        # we are exiting the table body
        # no data will be processed after this.
        if tag == self.TBODY:
            self.inside_tbody = False

        # exiting the table data and maybe moving td or tr element
        elif self.inside_tbody and self.inside_row and tag == self.TD:
            self.inside_row = False
            self.current_item = None

        # exiting the tr element, which means all necessary data
        # for a torrent has been extracted, we should save it
        # and clean the object's state.
        elif self.inside_tbody and tag == self.TR:
            self.current_result['leech'] = self.current_result['leeches']
            prettyPrinter(self.current_result)
            self.current_result = {}
            self.current_item = None


PAGINATION_PATTERN = re.compile('<li class="last"><a href="/search/(.*)/([0-9])/">Last</a></li>')  # noqa
DOWNLOAD_PATTERN = re.compile('<a class\="(.*) btn-(.*)" target\="_blank" href\="(.*)"><span class\="icon"><i class\="flaticon-torrent-download"></i></span>ITORRENTS MIRROR</a>')  # noqa


class leetx(object):
    url = LEETX_DOMAIN
    name = "1337x"
    supported_categories = {
        'all': 'All',
        'movies': 'Movies',
        'tv': 'TV',
        'music': 'Music',
        'games': 'Games',
        'anime': 'Anime',
        'software': 'Apps'
    }

    def download_torrent(self, info):
        # since 1337x does not provide torrent links in the search results,
        # we will have to fetch the page and extract the torrent link
        # and then call the download_file function on it.
        torrent_page = retrieve_url(info)
        torrent_link_match = DOWNLOAD_PATTERN.search(torrent_page)
        if torrent_link_match and torrent_link_match.groups():
            torrent_file = torrent_link_match.groups()[2].replace("http", "https")  # noqa
            print(download_file(torrent_file))
        else:
            print('')

    def search(self, what, cat='all'):
        cat = cat.lower()

        # decide which type of search to perform based on category
        search_page = "search" if cat == 'all' else 'category-search'
        search_url = "{url}/{search_page}/{search_query}/".format(
            url=self.url, search_page=search_page, search_query=what)

        # apply search category to url, if any.
        if cat != 'all':
            search_url += self.supported_categories[cat] + "/"

        # download the page
        data = retrieve_url(search_url + "1/")

        # extract no of pages to be extracted through pagination
        more_pages = 1
        pagination_match = PAGINATION_PATTERN.search(data)
        if pagination_match and pagination_match.groups()[1].isdigit():
            more_pages = int(pagination_match.groups()[1])

        parser = LeetxParser()
        parser.feed(data)
        parser.close()

        # we start the loop from 2 because we are already done first page.
        # the +2 at the end of the range because range(0, 100) is [0,1..,98,99]
        # shifing the end page by 2 positions will balance the number of pages.
        for current_page in range(2, more_pages + 2):
            # repeat
            data = retrieve_url(search_url + str(current_page) + "/")
            parser.feed(data)
            parser.close()
