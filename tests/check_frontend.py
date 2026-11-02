from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


class ScriptParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.external = []
        self.inline = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            attrs = dict(attrs)
            self.current = {"src": attrs.get("src"), "body": ""}
            if self.current["src"]:
                self.external.append(self.current["src"])

    def handle_data(self, data):
        if self.current is not None and not self.current["src"]:
            self.current["body"] += data

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.current is not None:
            if not self.current["src"] and self.current["body"].strip():
                self.inline.append(self.current["body"])
            self.current = None


def main():
    index = STATIC / "index.html"
    parser = ScriptParser()
    parser.feed(index.read_text(encoding="utf-8"))
    missing = []
    for src in parser.external:
        if src.startswith(("http://", "https://")):
            continue
        path = (STATIC / src.lstrip("/")).resolve()
        if not path.is_file() or STATIC.resolve() not in path.parents:
            missing.append(src)
    if missing:
        raise SystemExit("Missing frontend assets: " + ", ".join(missing))
    if not parser.inline:
        raise SystemExit("No application script found in index.html")
    node = shutil.which("node")
    if not node:
        raise SystemExit("Node.js is required for frontend syntax validation")
    with tempfile.TemporaryDirectory() as tmp:
        for i, source in enumerate(parser.inline):
            path = Path(tmp) / f"inline-{i}.js"
            path.write_text(source, encoding="utf-8")
            subprocess.run([node, "--check", str(path)], check=True)
    for path in (STATIC / "cloud-sync.js",):
        if path.exists():
            subprocess.run([node, "--check", str(path)], check=True)
    print("Frontend assets and JavaScript syntax validated.")


if __name__ == "__main__":
    main()
