# -*- coding: utf-8 -*-
import os
import sys
import logging
import contextlib
from collections import OrderedDict

from pyblish import api as pyblish

import ix
from . import lib
import pyblish.api

from openpype.pipeline import (
    register_loader_plugin_path,
    register_inventory_action_path,
    register_creator_plugin_path,
    AVALON_CONTAINER_ID,
)
from openpype.tools.utils import host_tools
from openpype.host import HostBase, ILoadHost, IWorkfileHost

from openpype.hosts.clarisse import CLARISSE_ROOT_DIR


PLUGINS_DIR = os.path.join(CLARISSE_ROOT_DIR, "plugins")
PUBLISH_PATH = os.path.join(PLUGINS_DIR, "publish")
LOAD_PATH = os.path.join(PLUGINS_DIR, "load")
CREATE_PATH = os.path.join(PLUGINS_DIR, "create")
INVENTORY_PATH = os.path.join(PLUGINS_DIR, "inventory")

OPENPYPE_ATTR_PREFIX = "openpype_"

self = sys.modules[__name__]
self._menu = "OpenPype>"
self._menu_callbacks = {}    # store custom menu callbacks, see _install_menu


class ClarisseHost(HostBase, IWorkfileHost, ILoadHost):
    name = "clarisse"

    def __init__(self):
        super(ClarisseHost, self).__init__()
        self._op_events = {}

    def install(self):
        pyblish.api.register_plugin_path(PUBLISH_PATH)
        pyblish.api.register_host("clarisse")

        register_loader_plugin_path(LOAD_PATH)
        register_creator_plugin_path(CREATE_PATH)
        register_inventory_action_path(INVENTORY_PATH)

        _install_menu()

    def open_workfile(self, filepath):
        return ix.load_project(str(filepath))

    def save_workfile(self, filepath=None):
        return ix.save_project(filepath)

    def work_root(self, session):
        work_dir = session.get("AVALON_WORKDIR")
        scene_dir = session.get("AVALON_SCENEDIR")
        if scene_dir:
            return os.path.join(work_dir, scene_dir)
        else:
            return work_dir

    def get_current_workfile(self):
        return get_current_clarisseproject()

    def workfile_has_unsaved_changes(self):
        return ix.check_need_save()

    def get_workfile_extensions(self):
        return [".project"]

    def gather_containers(self):
        """gathers all objects/ project item class to a list
        Only projectitems with openpype_id are taken into accound.
        No filtering, both enabled and disabled objects are accounted for.
        returns: list

        could be cleaner thou... next time...
        """
        all_files = []
        class_names = ix.api.CoreStringArray(1)
        class_names[0] = "ProjectItem"
        empty_mask = ix.api.CoreBitFieldHelper()
        all_objects = ix.api.OfObjectArray()
        root_context = ix.application.get_factory().get_root()
        root_context.get_all_objects(class_names, all_objects, empty_mask)
        for f in range(all_objects.get_count()):
            item = ix.item_exists(str(all_objects[f]))
            try:
                # we check for any item with filename but we want to
                # avoid children of a reference context
                if item.attrs.filename:
                    #check for references
                    if ix.get_item(str(item.get_parent_item())).is_reference():
                        # check parent if openpype attribute
                        if item.get_parent_item().attribute_exists("openpype_id"):
                            refed_item = item.get_parent_item()
                    else:
                        # check for any other item with file in it
                        # can be a texture map or vdb item or obj
                        if item.attribute_exists("openpype_id"):
                            refed_item = item

                    all_files.append(refed_item)
            except:
                pass

            # we need to include also all possible image layers where
            # openpype attribute is found
            if item.get_class_name() == "Image":
                sourced_image = item.get_module()
                for a in range(sourced_image.get_all_layers().get_count()):
                    layer = sourced_image.get_layers()[a].get_object()
                    try:
                        if layer.attribute_exists("openpype_id"):
                            all_files.append(layer)
                    except:
                        pass

        return all_files


    def get_containers(self):
        """Get containers.
        Currently just references are beeing accounted for.
        """
        all_items = self.gather_containers()
        for projectitem in all_items:
            ctx = ix.item_exists(str(projectitem))
            id = ctx.get_attribute("openpype_id").get_string()
            name = ctx.get_attribute("openpype_name").get_string()
            print("Container id/name/context", id, name, ctx)
            print("CTX", ctx)
            parsed = parse_container(ctx)
            yield parsed


    @contextlib.contextmanager
    def maintained_selection(self):
        with lib.maintained_selection():
            yield


class clarisse_project_fileLogHandler(logging.Handler):
    def emit(self, record):
        entry = self.format(record)
        clarisse_project_file = get_current_clarisseproject()
        if clarisse_project_file:
            clarisse_project_file.Print(entry)


def _install_menu():
    """Install OpenPype menu into Clarisse main menu"""

    def add_command_callback(menu,
                             name,
                             callback):
        """Helper function to add menu command with Python callback

        This allows us to avoid passing all commands as string script, like:
            menu.add_command_as_script(
                "ScriptingPython2",
                "Menu>Command",
                "import avalon.tools.creator as tool; tool.show()"
            )
        Clarisse 5 running python2.7 should use ScriptingPython2
        Clarisse 5 running python3.7 should use ScriptingPython3
        """

        # Store the callback
        self._menu_callbacks[name] = callback

        # check what python are we running:
        if sys.version_info.major == 3:
            py_clarisse_version = "ScriptingPython3"
        else:
            py_clarisse_version = "ScriptingPython2"

        # Build the call by name (escape any extra ' in name)
        cmd = (
            "import openpype.hosts.clarisse.api.pipeline; "
            "openpype.hosts.clarisse.api.pipeline._menu_callbacks['{name}']()"
        ).format(name=name.replace("'", "\'"))
        menu.add_command_as_script("{}".format(py_clarisse_version),
                                   name,
                                   cmd)

    menu = ix.application.get_main_menu()

    # Build top menu entry
    menu_name = self._menu   # get menu name
    menu.add_command(menu_name)

    # Add commands
    add_command_callback(menu, menu_name + "Create...",
                         callback=lambda: host_tools.show_creator())
    add_command_callback(menu, menu_name + "Load...",
                         callback=lambda: host_tools.show_loader(
                             use_context=True))
    add_command_callback(menu, menu_name + "Publish...",
                         callback=lambda: host_tools.show_publish())
    add_command_callback(menu, menu_name + "Manage...",
                         callback=lambda: host_tools.show_scene_inventory())
    add_command_callback(menu, menu_name + "Library...",
                         callback=lambda: host_tools.show_library_loader())

    menu.add_command(menu_name + "{Work}")

    add_command_callback(menu, menu_name + "Work Files",
                         callback=lambda: host_tools.show_workfiles())

    menu.add_command(menu_name + "{Utilities}")

    from .command import reset_frame_range, reset_resolution, set_project_fps

    add_command_callback(menu, menu_name + "Reset resolution",
                         callback=lambda: reset_resolution())

    add_command_callback(menu, menu_name + "Reset frame range",
                         callback=lambda: reset_frame_range())

    add_command_callback(menu, menu_name + "Set Project FPS",
                         callback=lambda: set_project_fps())

def imprint(node, data, group="openpype"):
    """Store string attributes with value on a node

    Args:
        node (framework.PyOfObject): The node to imprint data on.
        data (dict): Key value pairs of attributes to create.
        group (str): The Group to add the attributes to.

    Returns:
        None

    """
    for attr, value in data.items():
        # prefix the attribute
        pype_attr = OPENPYPE_ATTR_PREFIX + attr

        # Create the attribute
        node.add_attribute(pype_attr,
                           ix.api.OfAttr.TYPE_STRING,
                           ix.api.OfAttr.CONTAINER_SINGLE,
                           ix.api.OfAttr.VISUAL_HINT_DEFAULT,
                           group)

        # Set the attribute's value
        node.get_attribute(pype_attr)[0] = str(value)


def imprint_container(node, name, namespace, context, loader):
    """Imprint `node` with container metadata.

    Arguments:
        node (framework.PyOfObject): The node to containerise.
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str): Name of loader used to produce this container.

    Returns:
        None

    """

    data = [
        ("schema", "openpype:container-2.0"),
        ("id", AVALON_CONTAINER_ID),
        ("name", name),
        ("namespace", namespace),
        ("loader", loader),
        ("representation", context["representation"]["_id"])
    ]

    # We use an OrderedDict to make sure the attributes
    # are always created in the same order. This is solely
    # to make debugging easier when reading the values in
    # the attribute editor.
    imprint(node, OrderedDict(data))


def parse_container(node):
    """Returns imprinted container data of a tool

    This reads the imprinted data from `imprint_container`.

    """
    # If not all required data return None
    required = ['id', 'schema', 'name',
                'namespace', 'loader', 'representation']

    data = {}
    for key in required:
        attr = OPENPYPE_ATTR_PREFIX + key
        if not node.attribute_exists(attr):
            return

        value = node.get_attribute(attr)[0]
        data[key] = value

    # Store the node's name
    data["objectName"] = node.get_full_name()

    # Store reference to the node object
    data["node"] = node

    return data


def get_current_clarisseproject():
    """Hack to get current clarisse_project_file in this session"""
    current_filepath = ix.application.get_factory().get_vars().get("PNAME").get_string() + ".project"  # noqa
    # current_filepath = ix.application.get_current_project_filename()
    return current_filepath


@contextlib.contextmanager
def clarisse_project_file_lock_and_undo_chunk(clarisse_project_file, undo_queue_name="Script CMD"):
    """Lock clarisse_project_file and open an undo chunk during the context"""
    try:
        ix.begin_command_batch("Avalon: project undo")
        yield
    finally:
        ix.end_command_batch()
