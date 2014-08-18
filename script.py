# -*- coding: utf-8 -*-

import os
import sys

import xbmc
import xbmcaddon
import xbmcgui

from scraper import CaoliuScraper

addon = xbmcaddon.Addon(id='script.image.caoliu')
addon_path = addon.getAddonInfo('path')
addon_name = addon.getAddonInfo('name')
reload(sys)
sys.setdefaultencoding('utf8')

class GUI(xbmcgui.WindowXML):

    CONTROL_MAIN_IMAGE = 100
    ACTION_PREVIOUS_MENU = [9, 92, 10]
    ACTION_EXIT_SCRIPT = [13]
    ACTION_DOWN = [4]
    ACTION_UP = [3]
    ACTION_PLAY = [79]

    def __init__(self, *args, **kwargs):
        path = addon.getSetting('download_path')
        url = addon.getSetting('url')
        if url[-1:] != '/':
            url = url + '/'
        self.log(url)
        self._scraper = kwargs.get('scraper')(path, url, self._on_downloaded, 
                                              int(addon.getSetting('cache_post')),
                                              int(addon.getSetting('thread_count')),
                                              int(addon.getSetting('timeout')))
        self._scraper.start()
        xbmcgui.WindowXML.__init__(self)

    def onInit(self):
        self.log('onInit')

        self._image_list = self.getControl(self.CONTROL_MAIN_IMAGE)
        self._window = xbmcgui.Window(xbmcgui.getCurrentWindowId())

        self._post = self._scraper.get_post()
        self.showPhotos()

        self.setFocus(self._image_list)
        self.log('onInit finished')

    def _on_downloaded(index):
        if index == self._image_list.getSelectedPosition():
            self._image_list.getSelectedItem().setIconImage(self._post['imgs'][index])
        return

    def onAction(self, action):
        action_id = action.getId()
        if action_id in self.ACTION_PREVIOUS_MENU:
            self._scraper.stop()
            self.close()
        elif action_id in self.ACTION_EXIT_SCRIPT:
            self._scraper.stop()
            self.close()
        elif action_id in self.ACTION_DOWN:
            self._post = self._scraper.get_next_post()
            self.showPhotos()
        elif action_id in self.ACTION_UP:
            self._post = self._scraper.get_prev_post()
            self.showPhotos()
        elif action_id in self.ACTION_PLAY:
            return
            self.startSlideshow()

    def onClick(self, controlId):
        return
        self._post = self.caoliu.getList()
        self.showPhotos()

    def showPhotos(self):
        self.log('showPhoto')
        if len(self._post) == 0:
            self._window.setProperty('Title', '网络超时')
            return

        self._image_list.reset()
        self._window.setProperty('Title', self._post['title'])
        for img in self._post['imgs']:
            img_path = img['path']
            li = xbmcgui.ListItem(iconImage=img_path)
            self._image_list.addItem(li)

    def startSlideshow(self):
        self.log('startSlideshow')
        params = {'url': self._post[self._index]['url']}
        url = 'plugin://%s/?%s' % (addon.getAddonInfo('id'), urllib.urlencode(params))
        self.log('startSlideshow using url=%s' % url)
        xbmc.executebuiltin('Slideshow(%s, recursive)' % url)
        self.log('startSlideshow finished')

    def log(self, msg):
        xbmc.log('[CaoliuGUI]: %s' % msg)


def clear():
    path = addon.getSetting('download_path')
    try:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
        xbmcgui.Dialog().notification('提示', '缓存已清空')
    except:
        xbmcgui.Dialog().notification('提示', '清空缓存失败')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == 'clear':
            clear()
    else:
        if addon.getSetting('download_path') == '':
            addon.openSettings()
        if addon.getSetting('download_path') != '':
            gui = GUI(u'script-caoliu-main.xml', addon_path, "Default", session=None, scraper=CaoliuScraper).doModal()
            del gui
        else:
            xbmcgui.Dialog().notification('提示', '下载路径不能为空')
