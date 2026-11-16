# SPDX-License-Identifier: GPL-3.0-or-later
"""Local editor API isolation and editable-artboard persistence."""

import base64
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from theme_builder import Server, Studio
from theme_media import png


class ThemeStudioHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.server = Server(self.temp.name)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = "http://127.0.0.1:" + str(self.server.server_port)

    def request(self, action, data=None, token=True, origin=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Studio-Token"] = self.server.token
        if origin:
            headers["Origin"] = origin
        req = Request(
            self.base + "/api/action",
            json.dumps(dict(action=action, **(data or {}))).encode(),
            headers,
        )
        return json.loads(urlopen(req, timeout=10).read())

    def test_origin_token_and_real_edit_preview_flow(self):
        with urlopen(self.base + "/guide") as guide:
            self.assertIn(b"Theme Studio", guide.read())
        with self.assertRaises(HTTPError):
            self.request("state", token=False)
        with self.assertRaises(HTTPError):
            self.request("state", origin="https://example.com")
        result = self.request(
            "field", dict(section="theme", key="header", value="My header")
        )
        self.assertEqual(result["state"]["config"]["theme"]["header"], "My header")
        with urlopen(self.base + "/api/preview?token=" + self.server.token) as result:
            self.assertEqual(Image.open(io.BytesIO(result.read())).size, (256, 396))
        with self.assertRaises(HTTPError):
            urlopen(self.base + "/api/asset?path=../secret&token=" + self.server.token)

    def test_editable_layers_survive_a_new_server(self):
        data = (
            "data:image/png;base64,"
            + base64.b64encode(png(Image.new("RGBA", (32, 32), "red"))).decode()
        )
        document = dict(
            width=32,
            height=32,
            index=0,
            layers=[
                dict(
                    name="Red", visible=True, opacity=1, blend="source-over", data=data
                )
            ],
        )
        self.request(
            "artboard-save", dict(path="icons/folder.png", data=data, document=document)
        )
        reopened = Studio(self.temp.name)
        result = reopened.action("artboard-load", dict(path="icons/folder.png"))[
            "result"
        ]
        self.assertEqual(result["layers"][0]["name"], "Red")
        bad = copy.deepcopy(document)
        bad["width"] = 99999
        with self.assertRaises(HTTPError):
            self.request(
                "artboard-save", dict(path="icons/folder.png", data=data, document=bad)
            )

    def test_shared_splash_project_builds_into_theme(self):
        from splash_project import Workspace
        from theme_validate import splash_info

        folder = Path(self.temp.name) / "splash"
        folder.mkdir()
        source = Path(self.temp.name) / "top.png"
        Image.new("RGB", (256, 192), "navy").save(source)
        workspace = Workspace(folder)
        state = workspace.state
        state["paths"]["top"] = workspace.reference(workspace.import_asset(source))
        state["options"]["duration"] = "1"
        workspace.save(state)
        result = self.request("splash-build")
        data = (Path(self.temp.name) / "theme/splash.gsp").read_bytes()
        self.assertEqual(result["result"], len(data))
        self.assertEqual(splash_info(data)["layers"], 1)


if __name__ == "__main__":
    unittest.main()
