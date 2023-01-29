import os
from pprint import pformat
import pyblish.api

from openpype.hosts.clarisse.api.exports import execute_usd_export
from openpype.pipeline import publish

import ix


class ExtractUSD(publish.Extractor):
    order = pyblish.api.ExtractorOrder
    label = "Extract USD"
    hosts = ["clarisse"]
    families = ["usd"]

    def process(self, instance):
        self.log.info("instance.data: `{}`".format(
            pformat(instance.data)))

        item = instance.data["clarisse_geo_context"]
        options_ui = instance.data["export_ui_object"]

        execute_usd_export(options_ui)

        sel_item = ix.get_item(str(item))
        filepath = sel_item.attrs.filename[0]

        self.log.info('Exported file: {}'.format(filepath))

        assert os.path.isfile(filepath)

        folder, file = os.path.split(filepath)
        filename, ext = os.path.splitext(file)

        representation = {
            "name": ext.lstrip("."),
            "ext": ext.lstrip("."),
            "files": file,
            "stagingDir": folder,
        }

        self.log.info('representations: {}'.format(representation))

        if "representations" not in instance.data:
            instance.data["representations"] = []

        instance.data["representations"].append(representation)
