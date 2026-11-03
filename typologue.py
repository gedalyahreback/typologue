"""Local browser interface for the Typologue prototype."""
import base64
import binascii
import io
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from zipfile import ZipFile

from fontTools.designspaceLib import AxisDescriptor, DesignSpaceDocument, SourceDescriptor
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont, TTLibError
from fontTools.ufoLib import UFOWriter
from fontTools.varLib import build
from fontTools.varLib.errors import VarLibError
from fontTools.varLib.instancer import instantiateVariableFont

from build_v3 import axes, static_instance

MAX_REQUEST_BYTES = 48 * 1024 * 1024


def inspect(font, character):
    glyph_set = font.getGlyphSet()
    glyph_name = (font.getBestCmap() or {}).get(ord(character))
    result = {
        "name": font["name"].getDebugName(4),
        "axes": axes(font),
        "count": len(glyph_set.keys()),
        "em": font["head"].unitsPerEm,
        "glyph": None,
    }
    if glyph_name is not None:
        outline = DecomposingRecordingPen(glyph_set)
        glyph_set[glyph_name].draw(outline)
        svg = SVGPathPen(None)
        outline.replay(svg)
        result["glyph"] = {"name": glyph_name, "path": svg.getCommands(),
                           "width": glyph_set[glyph_name].width}
    return result


def export_sources(font, directory):
    """Export editable default outlines, with an axis-bearing Designspace for VFs."""
    document = DesignSpaceDocument()
    default = {}
    font_axes = axes(font)
    for axis in font_axes:
        descriptor = AxisDescriptor()
        descriptor.name = descriptor.tag = axis["tag"]
        descriptor.minimum = axis["min"]
        descriptor.default = axis["default"]
        descriptor.maximum = axis["max"]
        document.addAxis(descriptor)
        default[descriptor.name] = descriptor.default

    locations = [("Default", default)]
    for axis in document.axes:
        for label, value in (("Min", axis.minimum), ("Max", axis.maximum)):
            if value != axis.default:
                locations.append((f"{axis.tag}-{label}", {**default, axis.name: value}))

    unicodes = {}
    for codepoint, name in (font.getBestCmap() or {}).items():
        unicodes.setdefault(name, []).append(codepoint)

    for label, location in locations:
        instance = instantiateVariableFont(font, location) if font_axes else font
        filename = f"{label}.ufo"
        glyph_set = instance.getGlyphSet()
        with UFOWriter(directory / filename, formatVersion=3) as writer:
            info = type("FontInfo", (), {})()
            info.familyName = font["name"].getDebugName(1) or "Typologue"
            info.styleName = label
            info.unitsPerEm = font["head"].unitsPerEm
            writer.writeInfo(info)
            ufo_glyphs = writer.getGlyphSet()
            for name in glyph_set.keys():
                glyph = glyph_set[name]
                metadata = type("GlyphInfo", (), {})()
                metadata.width = glyph.width
                metadata.unicodes = unicodes.get(name, [])
                ufo_glyphs.writeGlyph(name, metadata, glyph.drawPoints)
            ufo_glyphs.writeContents()
            writer.writeLayerContents()

        source = SourceDescriptor()
        source.filename = filename
        source.name = label
        source.location = location
        document.addSource(source)

    document.write(directory / "family.designspace")


def merge_family(files, weights, directory):
    """Build one weight axis from compatible static TrueType masters."""
    if len(files) != 2:
        raise ValueError("Choose two static TrueType masters in the comparison panel.")
    low, high = map(float, weights)
    if not 1 <= low < high <= 1000:
        raise ValueError("Master weights must increase within 1–1000.")
    document = DesignSpaceDocument()
    axis = AxisDescriptor()
    axis.name, axis.tag = "Weight", "wght"
    axis.minimum = axis.default = low
    axis.maximum = high
    document.addAxis(axis)
    reference = None
    for index, (data, weight) in enumerate(zip(files, (low, high))):
        path = directory / f"master-{index}.ttf"
        path.write_bytes(base64.b64decode(data, validate=True))
        with TTFont(path) as font:
            if "glyf" not in font or "fvar" in font or font.flavor:
                raise ValueError("Each master must be a static, uncompressed TrueType font.")
            glyph_order = font.getGlyphOrder()
            glyphs = font["glyf"]
            topology = {}
            for name in glyph_order:
                glyph = glyphs[name]
                if glyph.isComposite():
                    topology[name] = [component.glyphName for component in glyph.components]
                else:
                    _, endpoints, flags = glyph.getCoordinates(glyphs)
                    topology[name] = (list(endpoints), [flag & 1 for flag in flags])
            signature = (font["head"].unitsPerEm, glyph_order, font.getBestCmap(), topology)
            if reference is not None:
                if signature[:3] != reference[:3]:
                    raise ValueError("Masters need matching em sizes, glyph order, and Unicode maps.")
                mismatches = [name for name in glyph_order if topology[name] != reference[3][name]]
                if mismatches:
                    raise ValueError("Incompatible glyph topology: " + ", ".join(mismatches[:10]))
            reference = signature
        source = SourceDescriptor()
        source.path = str(path)
        source.name = path.stem
        source.location = {axis.name: weight}
        document.addSource(source)

    variable, _, _ = build(document, exclude=["MVAR"])
    result = io.BytesIO()
    variable.save(result)
    return result.getvalue()


def process(operation, payload):
    files = payload["fonts"]
    if operation == "inspect":
        character = payload["character"]
        if len(character) != 1 or 0xD800 <= ord(character) <= 0xDFFF:
            raise ValueError("Enter exactly one Unicode character.")
        results = []
        for data in files:
            try:
                with TTFont(io.BytesIO(base64.b64decode(data, validate=True))) as font:
                    results.append(inspect(font, character))
            except (TTLibError, ValueError, OSError, KeyError) as error:
                results.append({"error": str(error)})
        return "application/json", json.dumps(results).encode()

    if operation == "merge":
        with TemporaryDirectory() as temporary:
            return "font/ttf", merge_family(files, payload["weights"], Path(temporary))

    if operation not in ("instance", "sources") or len(files) != 1:
        raise ValueError("Choose one font for export.")
    with TemporaryDirectory() as temporary:
        directory = Path(temporary)
        source = directory / "input-font"
        source.write_bytes(base64.b64decode(files[0], validate=True))
        with TTFont(source) as font:
            if operation == "instance":
                limits = axes(font)
                if not limits:
                    raise ValueError("Static instance export requires a variable font.")
                requested = payload.get("location", {})
                location = {}
                for axis in limits:
                    value = float(requested.get(axis["tag"], axis["default"]))
                    if not axis["min"] <= value <= axis["max"]:
                        raise ValueError(f'{axis["tag"]} is outside its supported range.')
                    location[axis["tag"]] = value
                slant = float(payload.get("slant", 0))
                if not -45 <= slant <= 45:
                    raise ValueError("Choose a slant between −45 and 45 degrees.")
                output = directory / "instance"
                static_instance(source, output, location, slant)
                mime = "font/otf" if font.sfntVersion == "OTTO" else "font/ttf"
                return mime, output.read_bytes()

            export_sources(font, directory)
        archive = io.BytesIO()
        with ZipFile(archive, "w") as output:
            for path in sorted(directory.rglob("*")):
                if path.is_file() and path != source:
                    output.write(path, path.relative_to(directory))
        return "application/zip", archive.getvalue()


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, mime, content):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        if self.path == "/":
            self.respond(200, "text/html; charset=utf-8",
                         Path(__file__).with_name("typologue.html").read_bytes())
        else:
            self.send_error(404)

    def do_POST(self):
        origin = urlsplit(self.headers.get("Origin", ""))
        if origin.scheme != "http" or origin.netloc != f"127.0.0.1:{self.server.server_port}":
            self.send_error(403)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= MAX_REQUEST_BYTES:
                raise ValueError("Choose font files totaling less than 36 MB.")
            payload = json.loads(self.rfile.read(size))
            mime, content = process(self.path.removeprefix("/"), payload)
        except (ValueError, KeyError, TypeError, OSError, RuntimeError, TTLibError,
                binascii.Error, VarLibError) as error:
            self.respond(400, "text/plain; charset=utf-8", str(error).encode())
            return
        self.respond(200, mime, content)


if __name__ == "__main__":
    with HTTPServer(("127.0.0.1", 8765), Handler) as server:
        print("Open http://127.0.0.1:8765 in your browser.", flush=True)
        server.serve_forever()
