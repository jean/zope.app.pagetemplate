##############################################################################
#
# Copyright (c) 2001, 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""View ZPT Tests

$Id$
"""
import unittest

from zope.app import zapi
from zope.interface import Interface, implements

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.site.tests.placefulsetup import PlacefulSetup


class I1(Interface):
    pass

class C1:
    implements(I1)

class InstanceWithContext:
    def __init__(self, context):
        self.context = context

class InstanceWithoutContext:
    pass


class TestViewZPT(PlacefulSetup, unittest.TestCase):

    def setUp(self):
        super(TestViewZPT, self).setUp()
        self.t = ViewPageTemplateFile('test.pt')
        self.context = C1()

    def testNamespaceContextAvailable(self):
        context = self.context
        request = None

        namespace = self.t.pt_getContext(InstanceWithContext(context), request)
        self.failUnless(namespace['context'] is context)
        self.failUnless('views' in namespace)

    def testNamespaceHereNotAvailable(self):
        request = None
        self.assertRaises(AttributeError, self.t.pt_getContext,
                          InstanceWithoutContext(), request)

    def testViewMapper(self):
        the_view = "This is the view"
        the_view_name = "some view name"
        def ViewMaker(*args, **kw):
            return the_view

        from zope.component.interfaces import IPresentationRequest

        zapi.getService(None, zapi.servicenames.Presentation).provideView(
            I1,
            name=the_view_name,
            type=IPresentationRequest,
            maker=ViewMaker)

        class MyRequest:
            implements(IPresentationRequest)
            def getPresentationSkin(self):
                return '' # default

        request = MyRequest()

        namespace = self.t.pt_getContext(InstanceWithContext(self.context),
                                         request)
        views = namespace['views']
        self.failUnless(the_view is views[the_view_name])


class TestViewZPTContentType(unittest.TestCase):

    def testInitWithoutType(self):
        t = ViewPageTemplateFile('test.pt')
        t._cook_check()
        self.assertEquals(t.content_type, "text/html")

        t = ViewPageTemplateFile('testxml.pt')
        t._cook_check()
        self.assertEquals(t.content_type, "text/xml")

    def testInitWithType(self):
        t = ViewPageTemplateFile('test.pt', content_type="text/plain")
        t._cook_check()
        self.assertEquals(t.content_type, "text/plain")

        t = ViewPageTemplateFile('testxml.pt', content_type="text/plain")
        t._cook_check()
        # XXX: This is arguable.  Should automatic content type detection
        #      really override content type specified to the constructor?
        self.assertEquals(t.content_type, "text/xml")


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestViewZPT))
    suite.addTest(unittest.makeSuite(TestViewZPTContentType))
    return suite


if __name__ == '__main__':
    unittest.TextTestRunner().run(test_suite())
