##############################################################################
#
# Copyright (c) 2002 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE
#
##############################################################################
"""Expression engine configuration and registration.

Each expression engine can have its own expression types and base names.

$Id: engine.py,v 1.23 2004/03/02 14:24:31 srichter Exp $
"""
__metaclass__ = type # All classes are new style when run with Python 2.2+

import sys
from types import StringTypes

from zope.tales.expressions import PathExpr, StringExpr, NotExpr, DeferExpr
from zope.tales.pythonexpr import PythonExpr
from zope.tales.tales import ExpressionEngine, Context

from zope.component.exceptions import ComponentLookupError
from zope.proxy import removeAllProxies
from zope.security.proxy import ProxyFactory
from zope.security.builtins import RestrictedBuiltins
from zope.i18n.translate import Translator

from zope.app import zapi
from zope.app.i18n import ZopeMessageIDFactory as _
from zope.app.traversing.adapters import Traverser


class InlineCodeError(Exception):
    pass

def zopeTraverser(object, path_items, econtext):
    """Traverses a sequence of names, first trying attributes then items.
    """
    traverser = Traverser(object)
    return traverser.traverse(path_items,
                              request=getattr(econtext, 'request', None))


class ZopePathExpr(PathExpr):

    def __init__(self, name, expr, engine):
        super(ZopePathExpr, self).__init__(name, expr, engine, zopeTraverser)

class ZopePythonExpr(PythonExpr):

    def __call__(self, econtext):
        __traceback_info__ = self.text
        vars = self._bind_used_names(econtext, RestrictedBuiltins)
        return eval(self._code, vars)

class ZopeContext(Context):

    def setContext(self, name, value):
        # Hook to allow subclasses to do things like adding security proxies
        Context.setContext(self, name, ProxyFactory(value))

    def evaluateText(self, expr):
        text = self.evaluate(expr)
        if text is self.getDefault() or text is None:
            return text
        if isinstance(text, StringTypes):
            # text could be a proxied/wrapped object
            return text
        return unicode(text)

    def evaluateMacro(self, expr):
        macro = Context.evaluateMacro(self, expr)
        macro = removeAllProxies(macro)
        return macro

    def translate(self, msgid, domain=None, mapping=None, default=None):
        # When running Zope, request is a Proxy, but no mutation is done here,
        # so it is safe to remove all proxies
        request = removeAllProxies(self.request)
        # XXX should we cache the translator instance?
        translator = Translator(domain, request, self.context)
        return translator.translate(msgid, mapping, default=default)

    evaluateInlineCode = False

    def evaluateCode(self, lang, code):
        if not self.evaluateInlineCode:
            raise InlineCodeError, \
                  _('Inline Code Evaluation is deactivated, which means that '
                    'you cannot have inline code snippets in your Page '
                    'Template. Activate Inline Code Evaluation and try again.')
        try:
            service = zapi.getService(self.context, 'Interpreter')
        except ComponentLookupError, err:
            raise InlineCodeError, \
                  _('No interpreter service was found. This should never '
                    'happen, since Zope defines a global interpreter service.')
        interpreter = service.queryInterpreter(lang)
        if interpreter is None:
            error = _('No interpreter named "${lang_name}" was found.')
            error.mapping = {'lang_name': lang}
            raise InlineCodeError, error
                  
        globals = self.vars.copy()
        result = interpreter.evaluateRawCode(code, globals)
        # Add possibly new global variables.
        old_names = self.vars.keys()
        for name, value in globals.items():
            if name not in old_names:
                self.setGlobal(name, value)
        return result

class ZopeEngine(ExpressionEngine):

    def getContext(self, __namespace=None, **namespace):
        if __namespace:
            if namespace:
                namespace.update(__namespace)
            else:
                namespace = __namespace

        context = ZopeContext(self, namespace)

        # Put request into context so path traversal can find it
        if 'request' in namespace:
            context.request = namespace['request']

        # Put context into context so path traversal can find it
        # XXX: Change to container once the renaming has been done!
        if 'context' in namespace:
            context.context = namespace['context']

        return context

def Engine():
    e = ZopeEngine()
    for pt in ZopePathExpr._default_type_names:
        e.registerType(pt, ZopePathExpr)
    e.registerType('string', StringExpr)
    e.registerType('python', ZopePythonExpr)
    e.registerType('not', NotExpr)
    e.registerType('defer', DeferExpr)
    e.registerBaseName('modules', ProxyFactory(sys.modules))
    return e

Engine = Engine()

class AppPT:

    # Use our special engine
    pt_getEngineContext = Engine.getContext

    def pt_getEngine(self):
        return Engine
