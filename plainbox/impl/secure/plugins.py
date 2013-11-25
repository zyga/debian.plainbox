# This file is part of Checkbox.
#
# Copyright 2013 Canonical Ltd.
# Written by:
#   Zygmunt Krynicki <zygmunt.krynicki@canonical.com>
#
# Checkbox is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Checkbox is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Checkbox.  If not, see <http://www.gnu.org/licenses/>.

"""
:mod:`plainbox.impl.secure.plugins` -- interface for accessing extension points
===============================================================================

This module contains plugin interface for plainbox. Plugins are based on
pkg_resources entry points feature. Any python package can advertise the
existence of entry points associated with a given namespace. Any other
package can query a given namespace and enumerate a sequence of entry points.

Each entry point has a name and importable identifier. The identifier can
be imported using the load() method. A loaded entry point is exposed as an
instance of :class:`PlugIn`. A high-level collection of plugins (that may
eventually also query alternate backends) is offered by
:class:`PlugInCollection`.

Using :meth:`PlugInCollection.load()` one can load all plugins from
a particular namespace and work with them using provided utility methods
such as :meth:`PlugInCollection.get_by_name()` or
:meth:`PlugInCollection.get_all_names()`

The set of loaded plugins can be overridden by mock/patching
:meth:`PlugInCollection._get_entry_points()`. This is especially useful for
testing in isolation from whatever entry points may exist in the system.
"""

import abc
import collections
import contextlib
import logging
import os

import pkg_resources


logger = logging.getLogger("plainbox.secure.plugins")


class IPlugIn(metaclass=abc.ABCMeta):
    """
    Piece of code loaded at runtime, one of many for a given extension point
    """

    @abc.abstractproperty
    def plugin_name(self):
        """
        name of the plugin, may not be unique
        """

    @abc.abstractproperty
    def plugin_object(self):
        """
        external object
        """


class PlugIn(IPlugIn):
    """
    Simple plug-in that does not offer any guarantees beyond knowing it's name
    and some arbitrary external object.
    """

    def __init__(self, name, obj):
        """
        Initialize the plug-in with the specified name and external object
        """
        self._name = name
        self._obj = obj

    def __repr__(self):
        return "<{!s} plugin_name:{!r}>".format(
            type(self).__name__, self.plugin_name)

    @property
    def plugin_name(self):
        return self._name

    @property
    def plugin_object(self):
        return self._obj


class IPlugInCollection:
    """
    A collection of IPlugIn objects.
    """

    @abc.abstractmethod
    def get_by_name(self, name):
        """
        Get the specified plug-in (by name)
        """

    @abc.abstractmethod
    def get_all_names(self):
        """
        Get an iterator to a sequence of plug-in names
        """

    @abc.abstractmethod
    def get_all_plugins(self):
        """
        Get an iterator to a sequence plug-ins
        """

    @abc.abstractmethod
    def get_all_items(self):
        """
        Get an iterator to a sequence of (name, plug-in)
        """

    @abc.abstractmethod
    def load(self):
        """
        Load all plug-ins.

        This method loads all plug-ins from the specified name-space.  It may
        perform a lot of IO so it's somewhat slow / expensive on a cold disk
        cache.
        """

    @abc.abstractmethod
    @contextlib.contextmanager
    def fake_plugins(self, plugins):
        """
        Context manager for using fake list of plugins

        :param plugins: list of PlugIn-alike objects

        The provided list of plugins overrides any previously loaded
        plugins and prevent loading any other, real, plugins. After
        the context manager exits the previous state is restored.
        """


class PlugInCollectionBase(IPlugInCollection):
    """
    Base class that shares some of the implementation with the other
    PlugInCollection implemenetations.
    """

    def __init__(self, load=False, wrapper=PlugIn):
        """
        Initialize a collection of plug-ins

        :param load:
            if true, load all of the plug-ins now
        :param wrapper:
            wrapper class for all loaded objects, defaults to :class:`PlugIn`
        """
        self._wrapper = wrapper
        self._plugins = collections.OrderedDict()
        self._loaded = False
        self._mocked_objects = None
        if load:
            self.load()

    def get_by_name(self, name):
        """
        Get the specified plug-in (by name)
        """
        return self._plugins[name]

    def get_all_names(self):
        """
        Get an iterator to a sequence of plug-in names
        """
        return list(self._plugins.keys())

    def get_all_plugins(self):
        """
        Get an iterator to a sequence plug-ins
        """
        return list(self._plugins.values())

    def get_all_items(self):
        """
        Get an iterator to a sequence of (name, plug-in)
        """
        return list(self._plugins.items())

    @contextlib.contextmanager
    def fake_plugins(self, plugins):
        """
        Context manager for using fake list of plugins

        :param plugins: list of PlugIn-alike objects

        The provided list of plugins overrides any previously loaded
        plugins and prevent loading any other, real, plugins. After
        the context manager exits the previous state is restored.
        """
        old_loaded = self._loaded
        old_plugins = self._plugins
        self._loaded = True
        self._plugins = collections.OrderedDict([
            (plugin.plugin_name, plugin)
            for plugin in sorted(
                plugins, key=lambda plugin: plugin.plugin_name)])
        try:
            yield
        finally:
            self._loaded = old_loaded
            self._plugins = old_plugins


class PkgResourcesPlugInCollection(PlugInCollectionBase):
    """
    Collection of plug-ins based on pkg_resources

    Instantiate with :attr:`namespace`, call :meth:`load()` and then access any
    of the loaded plug-ins using the API offered. All loaded objects are
    wrapped by a plug-in container. By default that is :class:`PlugIn` but it
    may be adjusted if required.
    """

    def __init__(self, namespace, load=False, wrapper=PlugIn):
        """
        Initialize a collection of plug-ins from the specified name-space.

        :param namespace:
            pkg_resources entry-point name-space of the plug-in collection
        :param load:
            if true, load all of the plug-ins now
        :param wrapper:
            wrapper class for all loaded objects, defaults to :class:`PlugIn`
        """
        self._namespace = namespace
        super(PkgResourcesPlugInCollection, self).__init__(load, wrapper)

    def load(self):
        """
        Load all plug-ins.

        This method loads all plug-ins from the specified name-space.  It may
        perform a lot of IO so it's somewhat slow / expensive on a cold disk
        cache.

        .. note::
            this method queries pkg-resources only once.
        """
        if self._loaded:
            return
        self._loaded = True
        iterator = self._get_entry_points()
        for entry_point in sorted(iterator, key=lambda ep: ep.name):
            try:
                obj = entry_point.load()
            except ImportError:
                logger.exception("Unable to import %s", entry_point)
            else:
                obj = self._wrapper(entry_point.name, obj)
                self._plugins[entry_point.name] = obj

    def _get_entry_points(self):
        """
        Get entry points from pkg_resources.

        This is the method you want to mock if you are writing unit tests
        """
        return pkg_resources.iter_entry_points(self._namespace)


class FsPlugInCollection(PlugInCollectionBase):
    """
    Collection of plug-ins based on filesystem entries

    Instantiate with :attr:`path` and :attr:`ext`, call :meth:`load()` and then
    access any of the loaded plug-ins using the API offered. All loaded plugin
    information files are wrapped by a plug-in container. By default that is
    :class:`PlugIn` but it may be adjusted if required.

    The name of each plugin is the base name of the plugin file, the object of
    each plugin is the text read from the plugin file.
    """

    def __init__(self, path, ext, load=False, wrapper=PlugIn):
        """
        Initialize a collection of plug-ins from the specified name-space.

        :param path:
            a PATH like variable that uses os.path.pathsep to separate multiple
            directory entries. Each directory is searched for (not recursively)
            for plugins.
        :param ext:
            extension of each plugin definition file
        :param load:
            if true, load all of the plug-ins now
        :param wrapper:
            wrapper class for all loaded objects, defaults to :class:`PlugIn`
        """
        self._path = path
        self._ext = ext
        super(FsPlugInCollection, self).__init__(load, wrapper)

    def load(self):
        """
        Load all plug-ins.

        This method loads all plug-ins from the search directories (as defined
        by the path attribute). Missing directories are silently ignored.
        """
        if self._loaded:
            return
        self._loaded = True
        iterator = self._get_plugin_files()
        for filename in sorted(iterator):
            try:
                with open(filename, encoding='UTF-8') as stream:
                    text = stream.read()
            except IOError as exc:
                logger.error("Unable to load %r: %s", filename, str(exc))
            else:
                obj = self._wrapper(filename, text)
                self._plugins[filename] = obj

    def _get_plugin_files(self):
        """
        Enumerate (generate) all plugin files according to 'path' and 'ext'
        """
        # Look in all parts of 'path' separated by standard system path
        # separator.
        for path in self._path.split(os.path.pathsep):
            # List all files in each path component
            try:
                entries = os.listdir(path)
            except OSError:
                # Silently ignore anything we cannot access
                continue
            # Look at each file there
            for entry in entries:
                # Skip files with other extensions
                if not entry.endswith(self._ext):
                    continue
                info_file = os.path.join(path, entry)
                # Skip all non-files
                if not os.path.isfile(info_file):
                    continue
                yield info_file
