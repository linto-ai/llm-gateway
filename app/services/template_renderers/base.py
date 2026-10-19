"""Plugin contract of the template renderers.

A renderer is an optional rendering feature a DOCX template opts into. It is a subclass of Renderer
registered with @register, in its own module of this package (modules are discovered automatically).

Two families, by what they transform:
  output       the Markdown of {{output}} written by the service prompt: prepare_output, format_output
  placeholder  the values filled by the extraction prompt: extraction_requests, before/after_substitution

The trigger is always in the template (placeholder syntax or custom document property). The prompts
only honour a contract, described by the renderer SPEC and published in docs/TEMPLATE_RENDERERS.md.
"""
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Tuple

logger = logging.getLogger(__name__)

CUSTOM_PROPS_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.custom-properties+xml"
CUSTOM_PROPS_NS = "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"

LISTS_KEY = "__lists__"  # placeholders entry holding the raw extracted lists

OUTPUT = "output"
PLACEHOLDER = "placeholder"
HOOKS_BY_FAMILY = {
    OUTPUT: {"prepare_output", "format_output"},
    PLACEHOLDER: {"extraction_requests", "before_substitution", "after_substitution"},
}


@dataclass(frozen=True)
class RendererSpec:
    trigger: str             # element of the template that turns the renderer on
    service_prompt: str      # what the service prompt ({{output}}) must produce
    placeholder_prompt: str  # what the placeholder instructions {{name: instruction}} must ask
    example: str


@dataclass
class RenderContext:
    """Everything a hook may need. props = custom document properties of the template, keys lower-cased."""
    placeholders: Dict[str, Any] = field(default_factory=dict)
    props: Dict[str, str] = field(default_factory=dict)
    set_run_text: Callable = None
    rescue: Callable = None


class Renderer:
    name: str = ""
    family: str = ""
    order: int = 100  # lower runs first within a hook
    spec: RendererSpec = None

    def extraction_requests(self, placeholders: List[str], parse, current_metadata: Dict[str, Any],
                            force: bool) -> Tuple[set, List[str]]:
        """Return (placeholder names handled here, extraction requests to add)."""
        return set(), []

    def before_substitution(self, doc, ctx: RenderContext) -> None:
        pass

    def after_substitution(self, doc, ctx: RenderContext) -> None:
        pass

    def prepare_output(self, doc, markdown: str, ctx: RenderContext) -> str:
        return markdown

    def format_output(self, doc, inserted_elements, ctx: RenderContext) -> None:
        pass


REGISTRY: List[Renderer] = []


def implemented_hooks(cls) -> set:
    return {h for hooks in HOOKS_BY_FAMILY.values() for h in hooks if getattr(cls, h) is not getattr(Renderer, h)}


def register(cls):
    """Class decorator: validate the plugin and add one instance to the registry."""
    if not cls.name or cls.family not in HOOKS_BY_FAMILY or not isinstance(cls.spec, RendererSpec):
        raise TypeError(f"{cls.__name__}: name, family ('output' or 'placeholder') and spec are required")
    foreign = implemented_hooks(cls) - HOOKS_BY_FAMILY[cls.family]
    if foreign:
        raise TypeError(f"{cls.__name__} ({cls.family}) implements hooks of another family: {sorted(foreign)}")
    if any(r.name == cls.name for r in REGISTRY):
        raise TypeError(f"renderer name '{cls.name}' already registered")
    REGISTRY.append(cls())
    REGISTRY.sort(key=lambda r: (r.order, r.name))
    return cls


def template_properties(doc) -> Dict[str, str]:
    """Custom document properties of the template (Word: File > Info > Properties > Custom)."""
    try:
        for part in doc.part.package.iter_parts():
            if getattr(part, "content_type", None) != CUSTOM_PROPS_CONTENT_TYPE:
                continue
            root = ET.fromstring(part.blob)
            props: Dict[str, str] = {}
            for prop in root.findall("p:property", {"p": CUSTOM_PROPS_NS}):
                value = next(iter(prop), None)
                props[(prop.get("name") or "").strip().lower()] = (
                    (value.text or "").strip() if value is not None else ""
                )
            return props
    except Exception:
        logger.debug("Could not read template custom properties", exc_info=True)
    return {}


def parse_placeholder(placeholder: str) -> Dict[str, Any]:
    """'name: instruction' -> {'name', 'description'} (same rule as DocumentTemplateService)."""
    name, _, description = placeholder.partition(":")
    return {"name": name.strip(), "description": description.strip() or None}


def csv_values(props: Dict[str, str], key: str) -> List[str]:
    return [v.strip() for v in props.get(key, "").split(",") if v.strip()]
