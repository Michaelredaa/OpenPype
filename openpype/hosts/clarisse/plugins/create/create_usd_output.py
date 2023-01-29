import ix

from openpype.hosts.clarisse.api.exports import export_usd_options_uiobject
from openpype.hosts.clarisse.api.lib import (
    get_current_frame,
    get_selected_context,
)
from openpype.hosts.clarisse.api.pipeline import imprint
from openpype.pipeline import LegacyCreator


class CreateUSDOutput(LegacyCreator):
    """Export a context as USD
    no shading will be exported, just geometry"""

    label = "USD export"
    family = "usd"
    icon = "magic"
    defaults = ["Main"]

    def __init__(self, *args, **kwargs):
        super(CreateUSDOutput, self).__init__(*args, **kwargs)

    def process(self):
        """Creator main entry point of usd.
        """
        # get selected context
        ctx_select = get_selected_context()
        assert ctx_select

        filepath = "$PDIR/cache/usd/%s.usd" % self.name

        # frame range
        export_settings = {
            "export_context": True,
            "filename": filepath,
            "default_prim": 1,
            "root_prim": '',  # instance.data['root_prim'],
            # "root_prim_name": "",
            "standalone": 0,  # flatten_usd
            "use_instances": 0,
            "export_invisible_objects": 0,
            "export_displacement": 0,
            "export_custom_attributes": 1,
            "custom_attributes_namespace": "",
            "animation_mode": get_current_frame(),  # current frame
            # "custom_frame": 0,
            # "custom_frame_range": [instance.data['start_frame'], instance.data['end_frame']],

        }

        node = export_usd_options_uiobject(selected_context=ctx_select, name=self.name,  options=export_settings)

        imprint(node, self.data, group="openpype")
