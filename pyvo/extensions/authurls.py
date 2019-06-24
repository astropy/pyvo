import collections
import logging

class AuthURLs():

    def __init__(self):
        self.full_urls = collections.defaultdict(set)
        self.base_urls = collections.defaultdict(set)

    def parse_capabilities(self, capabilities):
        for c in capabilities:
            for i in c.interfaces:
                for u in i.accessurls:
                    url = u.content
                    methods = set()

                    for sm in i.securitymethods:
                        if sm.standardid:
                            methods.add(sm.standardid)
                        else:
                            methods.add('anonymous')

                    if not methods:
                       methods.add('anonymous')

                    if u.use == 'full':
                        self.full_urls[url].update(methods)
                    if u.use == 'base' or u.use == 'dir':
                        self.base_urls[url].update(methods)

    def iterate_base_urls(self):
        def sort_by_len(x):
            return len(x[0])

        # Sort the base path matching URLs, so that
        # the longest URLs (the most specific ones, if
        # there is a tie) are used to determine the
        # auth method.
        for url, method in sorted(self.base_urls.items(),
                                  key=sort_by_len,
                                  reverse=True):
            yield url, method

    def allowed_auth_methods(self, url):
        logging.debug('Determining auth method for %s', url)

        if url in self.full_urls:
            methods = self.full_urls[url]
            logging.debug('Matching full url %s, methods %s', full_url, methods)
            return methods

        for base_url, methods in self.iterate_base_urls():
            if url.startswith(base_url):
                logging.debug('Matching base url %s, methods %s', base_url, methods)
                return methods

        logging.debug('No match, using anonymous auth')
        return {'anonymous'}

    def __repr__(self):
        urls = []

        for url, methods in self.full_urls.items():
            urls.append('Full match:' + url + ':' + str(methods))
        for url, methods in self.iterate_base_urls():
            urls.append('Base match:' + url + ':' + str(methods))

        return '\n'.join(urls)
