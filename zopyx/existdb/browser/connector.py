import urllib
import mimetypes
import fs
import fs.errors
import zExceptions
from fs.opener import opener
from fs.contrib.davfs import DAVFS
from Products.Five.browser import BrowserView
from zope.interface import implements
from zope.interface import implementer
from zope.publisher.interfaces import IPublishTraverse
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


from ZPublisher.Iterators import IStreamIterator

class webdav_iterator(file):

    implements(IStreamIterator)

    def __init__(self, handle, mode='rb', streamsize=1<<16):
        self.fp = handle.open('.', mode)
        self.streamsize = streamsize

    def next(self):
        data = self.fp.read(self.streamsize)
        if not data:
            raise StopIteration
        return data

    def __len__(self):
        cur_pos = self.fp.tell()
        self.fp.seek(0, 2)
        size = self.fp.tell()
        self.seek(cur_pos, 0)
        return size


@implementer(IPublishTraverse)
class Connector(BrowserView):
    
    template = ViewPageTemplateFile('connector_view.pt')

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self.subpath = []

    def __call__(self, *args, **kw):
        url = self.context.url + '/' + urllib.quote('/'.join(self.subpath))
        try:
            handle = DAVFS(url, credentials=dict(username='admin', password='pnmaster'))
        except fs.errors.ResourceNotFoundError:
            raise zExceptions.NotFound()
            
        if handle.isdir('.'):
            files = handle.listdirinfo(files_only=True)
            files = sorted(files)
            dirs = handle.listdirinfo(dirs_only=True)
            dirs = sorted(dirs)
            return self.template(
                    subpath='/'.join(self.subpath),
                    files=files, 
                    dirs=dirs)
        elif handle.isfile('.'):
            filename = self.subpath[-1]
            info = handle.getinfo('.')
            mt, encoding = mimetypes.guess_type(filename)
            self.request.response.setHeader('Content-Type', mt)
            if 'size' in info:
                self.request.response.setHeader('Content-Length', info['size'])
            return webdav_iterator(handle)
            return handle.open('.', 'rb').read()
        else:
            raise RuntimeError()

    def publishTraverse(self, request, name):
        if not hasattr(self, 'subpath'):
            self.subpath = []
        self.subpath.append(name)
        return self
