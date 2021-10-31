
import pyblish.api


class IntegrateInputLinks(pyblish.api.ContextPlugin):
    """Connecting version level dependency links"""

    order = pyblish.api.IntegratorOrder + 0.2
    label = "Connect Dependency InputLinks"

    def process(self, context):
        workfile = None
        publishing = []

        for instance in context:
            version_doc = instance.data.get("versionEntity")
            if not version_doc:
                self.log.debug("Instance %s doesn't have version." % instance)
                continue

            version_data = version_doc.get("data", {})
            families = version_data.get("families", [])
            self.log.debug(families)

            if "workfile" in families:
                workfile = instance
            else:
                publishing.append(instance)

        if workfile is None:
            self.log.warn("No workfile in this publish session.")
        else:
            workfile_version_doc = workfile.data["versionEntity"]
            # link all loaded versions in scene into workfile
            for version in context.data.get("loadedVersions", []):
                self.add_link(
                    link_type="reference",
                    input_id=version["version"],
                    version_doc=workfile_version_doc,
                )
            # link workfile to all publishing versions
            for instance in publishing:
                self.add_link(
                    link_type="generative",
                    input_id=workfile_version_doc["_id"],
                    version_doc=instance.data["versionEntity"],
                )

        # link versions as dependencies to the instance
        for instance in publishing:
            for input_version in instance.data.get("inputVersions") or []:
                self.add_link(
                    link_type="generative",
                    input_id=input_version,
                    version_doc=instance.data["versionEntity"],
                )

        self.write_links_to_database(context)

    def add_link(self, link_type, input_id, version_doc):
        from collections import OrderedDict
        from avalon import io
        # NOTE:
        # using OrderedDict() here is just for ensuring field order between
        # python versions, if we ever need to use mongodb operation '$addToSet'
        # to update and avoid duplicating elements in 'inputLinks' array in the
        # future.
        link = OrderedDict()
        link["type"] = link_type
        link["input"] = io.ObjectId(input_id)
        link["linkedBy"] = "publish"

        if "inputLinks" not in version_doc["data"]:
            version_doc["data"]["inputLinks"] = []
        version_doc["data"]["inputLinks"].append(link)

    def write_links_to_database(self, context):
        from avalon import io

        for instance in context:
            version_doc = instance.data.get("versionEntity")
            if version_doc is None:
                continue

            input_links = version_doc["data"].get("inputLinks")
            if input_links is None:
                continue

            io.update_one({"_id": version_doc["_id"]},
                          {"$set": {"data.inputLinks": input_links}})
