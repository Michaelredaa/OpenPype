import os
import pyblish.api
from openpype.hosts.clarisse.api.pipeline import get_export_containers
from openpype.pipeline import (
    legacy_io
)
import ix



class CollectUSDNode(pyblish.api.ContextPlugin):
    """Collect USD exports
    """

    order = pyblish.api.CollectorOrder - 0.01
    label = "Collect Clarisse USD Geometry"
    hosts = ["clarisse"]
    family = "model"

    def process(self, context):
        """collect usd instances in current file"""

        task = legacy_io.Session["AVALON_TASK"]

        geo_collection = get_export_containers(creatortype="geometry", class_type="UsdExportUI")

        self.log.info('Collected instances: {}'.format(geo_collection))
        # create instances
        for geo in geo_collection:
            item = ix.get_item(str(geo))
            geo_filename = item.attrs.filename[0]
            folder, file = os.path.split(geo_filename)
            geo_name = str(geo).split("/")[-1]
            instance = context.create_instance(name=str(geo_name))
            subset = geo_name

            data = {}
            data.update({
                "subset": subset,
                "asset": os.getenv("AVALON_ASSET", None),
                "label": str(geo_name),
                "publish": True,
                "family": "usd",
                "families": ["usd"],
                "setMembers": [""],
                "frameStart": context.data['frameStart'],
                "frameEnd": context.data['frameEnd'],
                "handleStart": context.data['handleStart'],
                "handleEnd": context.data['handleEnd'],
                "clarisse_geo_context": str(geo),
                "export_ui_object": str(geo)
            })

            if not os.path.isdir(folder):
                os.makedirs(folder)

            instance.context.data["cleanupFullPaths"].append(folder)

            instance.data.update(data)