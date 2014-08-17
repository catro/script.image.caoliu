# -*- coding: utf-8 -*-

import sys
import re
import urllib
import urllib2
import gzip
import StringIO
import os
import threading
import socket
import time
from Queue import Queue
try:
    import xbmc
    XBMC=True
except:
    XBMC=False

reload(sys)
sys.setdefaultencoding('utf8')

class Scraper(threading.Thread):
    def log(self, msg):
        if XBMC:
            xbmc.log('[%s]: %s' % (self.__class__.__name__, msg))
        else:
            print('[%s]: %s' % (self.__class__.__name__, msg))

    def __init__(self, download_path, host, on_downloaded=None, posts_cache_max=10, 
                 thread_count=100, timeout=10, retry_max=10):
        self._host = host
        self._download_path = download_path
        self._on_downloaded_callback = on_downloaded
        self._posts = []
        self._post_index = 0
        self._posts_cache = Queue(posts_cache_max)
        self._download_queue = Queue()
        self._threads = []
        self._running = True
        self._timeout = timeout
        socket.setdefaulttimeout(timeout)

        for i in range(thread_count):
            t = Downloader(retry_max, self._download_queue, self.on_downloaded)
            t.start()
            self._threads.append(t)

        threading.Thread.__init__(self)

    def _get_pages(self):
        raise NotImplementedError

    def _get_posts(self, url):
        raise NotImplementedError

    def _get_imgs(self, url):
        raise NotImplementedError

    def on_downloaded(self, post_title, img_index):
        if post_title == self._posts[self._post_index]['title']:
            self._on_downloaded_callback(img_index - 1)

    def get_post_title(self, index=-1):
        if index == -1:
            index = self._post_index
        else:
            self._post_index = index
        while len(self._posts) <= index:
            self._posts.append(self._posts_cache.get())
        return self._posts[index]

    def get_post(self, index=-1):
        if index == -1:
            index = self._post_index
        else:
            self._post_index = index
        while len(self._posts) <= index:
            try:
                self._posts.append(self._posts_cache.get(True, self._timeout))
            except:
                return []
        return self._posts[index]

    def get_next_post(self):
        self._post_index += 1
        return self.get_post()

    def get_prev_post(self):
        if self._post_index > 0:
            self._post_index -= 1
        return self.get_post()

    def run(self):
        for page in self._get_pages():
            for post in self._get_posts(page):
                self.log('Downloading ' + post['title'])
                try:
                    folder = self._download_path + '/' + post['title']
                    if not os.path.isdir(folder):
                        os.makedirs(folder)
                    imgs = self._get_imgs(post['url'])
                    for img in imgs:
                        path = folder + '/' + str(img['index']) + '.jpg'
                        img['path'] = path
                        img['title'] = post['title']
                        img['downloaded'] = False
                        self._download_queue.put(img)
                    self._posts_cache.put({'title': post['title'], 'imgs': imgs})
                except:
                    pass
                if self._running == False:
                    return

    def stop(self):
        self._running = False
        for t in self._threads:
            t.stop()

    def _open_url(self, url):
        try:
            req = urllib2.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) {0}{1}'.
                           format('AppleWebKit/537.36 (KHTML, like Gecko) ',
                                  'Chrome/28.0.1500.71 Safari/537.36'))
            req.add_header('Accept-encoding', 'gzip')
            response = urllib2.urlopen(req)
            httpdata = response.read()
            if response.headers.get('content-encoding', None) == 'gzip':
                httpdata = gzip.GzipFile(fileobj=StringIO.StringIO(httpdata)).read()
            response.close()
            match = re.compile('encodingt=(.+?)"').findall(httpdata)
            if len(match)<=0:
                match = re.compile('charset="(.+?)"').findall(httpdata)
            if len(match)<=0:
                match = re.compile('charset=(.+?)"').findall(httpdata)
            if len(match)>0:
                charset = match[0].lower()
                if charset == 'gb2312':
                    charset = 'gbk'
                if (charset != 'utf-8') and (charset != 'utf8'):
                    httpdata = httpdata.decode(charset)
                else:
                    httpdata = httpdata.decode('utf8')
        except:
            httpdata = ''

        return httpdata


class CaoliuScraper(Scraper):
    _root = 'thread0806.php'

    def _get_pages(self):
        pages = []
        for page in range(1, 100):
            pages.append(self._host + self._root + '?fid=8&page=%d' % page)
        return pages

    def _get_posts(self, url):
        posts = []
        data = self._open_url(url)
        find_re = re.compile(r'<tr align="center" class="tr3 t_one" .+?<a .+?<a href="(.+?)".+?>(.+?)</a>', re.DOTALL)

        data = find_re.findall(data)
        for item in data:
            if '<font' in item[1]:
                continue
            posts.append({'url': item[0], 'title': item[1]})
        return posts

    def _get_imgs(self, url):
        imgs = []
        url = self._host + url
        data = self._open_url(url)
        find_re = re.compile(r"input type='image' src='(.+?)'", re.DOTALL)
        data = find_re.findall(data)
        i = 0
        for img in data:
            i += 1
            imgs.append({'url': img, 'index': i})
        return imgs

class Downloader(threading.Thread):
    def __init__(self, retry_max, download_queue, on_downloaded):
        self._retry_max = retry_max
        self._download_queue = download_queue
        self._on_downloaded = on_downloaded
        self._running = True
        threading.Thread.__init__(self)

    def run(self):
        while self._running:
            img = self._download_queue.get()
            retry = 0
            tmp = img['path'] + '.tmp'
            while retry < self._retry_max:
                try:
                    if not os.path.isfile(img['path']):
                        self._download_file(img['url'], tmp)
                        os.rename(tmp, img['path'])
                    img['downloaded'] = True
                    self._on_downloaded(img['title'], img['index'])
                    break
                except:
                    retry += 1
            if os.path.isfile(tmp):
                os.remove(tmp)

    def _download_file(self, url, path):
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) {0}{1}'.
                       format('AppleWebKit/537.36 (KHTML, like Gecko) ',
                       'Chrome/28.0.1500.71 Safari/537.36'))
        with open(path, "wb") as code:
            code.write(urllib2.urlopen(req).read()) 

    def stop(self):
        self._running = False


try:
    import xbmc
except:
    index = 0
    post = {}
    def on_downloaded(idx):
        return
        if index == idx:
            print ('[Downloaded]: %s' % post['imgs'][index]['index'])

if __name__ == '__main__':
    try:
        import xbmc
    except:
        import msvcrt
        s = CaoliuScraper('images', on_downloaded)
        s.start()
        c = ''
        post = s.get_post()
        while c != 'x':
            if False:
                print ('Current post: %s(%d)' % (post['title'], len(post['imgs'])))
                if len(post['imgs']):
                    if post['imgs'][index]['downloaded']:
                        print ('Current image: %s' % (post['imgs'][index]['index']))
                    else:
                        print ('Downloading: %s' % (post['imgs'][index]['index']))
                else:
                    print ('No imgs')
            while c != 'x':
                c = msvcrt.getch()
                if c == 'j':
                    post = s.get_prev_post()
                    index = 0
                    break
                elif c == 'k':
                    post = s.get_next_post()
                    index = 0
                    break
                elif c == 'h':
                    if index > 0:
                        index -= 1
                        break
                elif c == 'l':
                    if index < len(post['imgs']) - 1:
                        index += 1
                        break

        s.stop()
