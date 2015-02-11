# -*- coding: utf-8 -*-

################################################################
# xmldirector.plonecore
# (C) 2014,  Andreas Jung, www.zopyx.com, Tuebingen, Germany
################################################################


import os
import operator
import fs.opener
import datetime
import lxml.etree
from zope.interface import implements
from xmldirector.plonecore.interfaces import ITransformerRegistry
from xmldirector.plonecore.logger import LOG


# The XSLT registrie stores pre-compiled XSLT transformations as a dictionary
# where the keys are composed of a tuple (family, transformer_name).  ``family``
# could be used to represent a project, a customer etc.  and
# ``transformer_name`` would represent the name of the XSLT transformation.
# Both ``family`` and ``transformer_name`` are completey arbitrary.


class XSLT1Wrapper(object):

    def __init__(self, transformer):
        self.transformer = transformer

    def __call__(self, root, conversion_context):
        return self.transformer(root)


class TransformerRegistry(object):

    implements(ITransformerRegistry)

    registry = {}

    def register_transformation(self, family, transformer_name, transformer_path, transformer_type='XSLT1'):
        """ Register a Transformation as tuple (family, transformer_name) """

        if transformer_type == 'python':
            # transformer_path is Python function here
            transform = transformer_path
            method_filename = transform.func_code.co_filename
            transformer_path = '{}(), {}'.format(transformer_path.func_name, transformer_path.func_code.co_filename)
            dir_handle = fs.opener.fsopendir('{}/..'.format(method_filename))
            info = dir_handle.getinfo(os.path.basename(method_filename))

        elif transformer_type == 'XSLT1':

            try:
                handle = fs.opener.opener.open(transformer_path)
            except Exception as e:
                raise ValueError(
                    'Transformation {}/{} not found ({}, {})'.format(family, transformer_name, transformer_path, e))

            with fs.opener.opener.open(transformer_path, 'rb') as fp:

                if transformer_path.startswith('/'):
                    transformer_path = 'file://' + transformer_path

                dir_handle = fs.opener.fsopendir('{}/..'.format(handle.name))
                info = dir_handle.getinfo(os.path.basename(handle.name))

                try:
                    xslt = lxml.etree.XML(fp.read())
                except lxml.etree.XMLSyntaxError as e:
                    raise ValueError(
                        'Transformation {}/{} could not be parsed ({}, {})'.format(family, transformer_name, e, transformer_path))

                try:
                    transform = lxml.etree.XSLT(xslt)
                except lxml.etree.XSLTParseError as e:
                    raise ValueError(
                        'Transformation {}/{} could not be parsed ({}, {})'.format(family, transformer_name, e, transformer_path))

        else:
            raise ValueError(u'Unsupported transformer type "{}"'.format(transformer_type))

        key = '{}::{}'.format(family, transformer_name)
        if key in self.registry:
            raise ValueError(
                'Transformation {}/{} already registered'.format(family, transformer_name))
    
        self.registry[key] = dict(
            transform=transform,
            path=transformer_path,
            type=transformer_type,
            family=family,
            name=transformer_name,
            info=info,
            registered=datetime.datetime.utcnow())

        LOG.info('Transformer registered ({}, {})'.format(key, transformer_path))

    def entries(self):
        result = self.registry.values()
        return sorted(result, key=operator.itemgetter('family', 'name'))

    def get_transformation(self, family, transformer_name):
        """ Return a pre-compiled XSLT transformation by (family, transformer_name) """

        key = '{}::{}'.format(family, transformer_name)
        if key not in self.registry:
            raise ValueError(
                'Transformation {}/{} not registered'.format(family, transformer_name))
        d = self.registry[key]
        if d['type'] == 'python':
            return d['transform']
        elif d['type'] == 'XSLT1':
            return XSLT1Wrapper(d['transform'])
        

    def clear(self):
        """ Remove all entries """
        self.registry.clear()

    def __len__(self):
        """ Return number of registered transformations """
        return len(self.registry)


TransformerRegistryUtility = TransformerRegistry()