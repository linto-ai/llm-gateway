"""Output tables: layout of the Markdown tables of the service output, driven by the template.

htmldocx inserts Markdown tables with no style and equal columns, and LibreOffice (PDF) ignores the
default table style. Properties of the template fix that:
  style_table          table styleId defined in the template; header look from its firstRow; "-"/"N/A" cells emptied
  table_widths         column percentages, applied when the column count matches ("5,55,7,20,13")
  table_align          left|center|right per column
  table_symbol_colors  symbol:hex pairs coloured inside cells ("►:C51C42,◆:1F8A5B")
Rows never split across pages whenever one of these properties is set.
"""
from copy import deepcopy
from typing import Dict

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from .base import OUTPUT, Renderer, RendererSpec, csv_values, logger, register

SPEC = RendererSpec(
    trigger="Propriétés personnalisées du template style_table, table_widths, table_align, table_symbol_colors.",
    service_prompt=(
        "Le prompt du service impose un tableau Markdown avec exactement le nombre de colonnes de table_widths, "
        "l'en-tête voulu, des cellules vides plutôt que « - », et les symboles exacts de table_symbol_colors "
        "(par exemple « A ► »). Ouvrir la réponse par un titre, jamais par le tableau nu : sinon Mistral "
        "entoure le tableau d'un bloc de code."
    ),
    placeholder_prompt="Aucune exigence : le tableau vient de {{output}}, pas de l'extraction.",
    example="style_table = CRSujets ; table_widths = 5,55,7,20,13 ; table_align = center,left,center,center,center",
)

EMPTY_CELLS = ("-", "–", "—", "N/A", "n/a")


def _symbol_colors(props):
    colors = {}
    for item in csv_values(props, "table_symbol_colors"):
        if ":" in item:
            sym, col = item.split(":", 1)
            if sym.strip() and col.strip():
                colors[sym.strip()] = col.strip().lstrip("#")
    return colors


def format_tables(doc, inserted_elements, props: Dict[str, str]) -> None:
    style_id = props.get("style_table", "")
    if style_id:
        known = {s.get(qn("w:styleId")) for s in doc.styles.element.findall(qn("w:style"))}
        if style_id not in known:
            logger.warning(f"style_table '{style_id}' is not a style of the template, ignored")
            style_id = ""
    try:
        widths = [float(x) for x in csv_values(props, "table_widths")]
    except ValueError:
        widths = []
    aligns = [a.lower() for a in csv_values(props, "table_align")]
    colors = _symbol_colors(props)
    if not (style_id or widths or aligns or colors):
        return

    section = doc.sections[-1]
    body_twips = int((section.page_width - section.left_margin - section.right_margin) / 635)
    for tbl in (e for e in inserted_elements if e.tag == qn("w:tbl")):
        rows = tbl.findall(qn("w:tr"))
        for tr in rows:
            trpr = tr.get_or_add_trPr()
            if trpr.find(qn("w:cantSplit")) is None:
                trpr.append(OxmlElement("w:cantSplit"))
        if style_id:
            _apply_style(tbl, rows, style_id)
        if widths:
            _apply_widths(tbl, rows, widths, body_twips)
        if aligns:
            _apply_align(rows, aligns)
        if colors:
            _apply_colors(tbl, colors)


def _apply_style(tbl, rows, style_id):
    tbl.tblPr.get_or_add_tblStyle().set(qn("w:val"), style_id)
    if rows:  # htmldocx forces bold on <th>; the style's firstRow decides
        for b in list(rows[0].iter(qn("w:b"))):
            b.getparent().remove(b)
    for tc in tbl.iter(qn("w:tc")):
        if "".join(t.text or "" for t in tc.iter(qn("w:t"))).strip() in EMPTY_CELLS:
            for t in tc.iter(qn("w:t")):
                t.text = ""


def _apply_widths(tbl, rows, widths, body_twips):
    grid = tbl.tblGrid.findall(qn("w:gridCol"))
    if len(widths) != len(grid):
        return
    total = sum(widths)
    twips = [int(body_twips * w / total) for w in widths]
    tblw = tbl.tblPr.find(qn("w:tblW"))
    if tblw is not None:
        tblw.set(qn("w:type"), "dxa")
        tblw.set(qn("w:w"), str(body_twips))
    tbl.tblPr.get_or_add_tblLayout().set(qn("w:type"), "fixed")
    for gc, w in zip(grid, twips):
        gc.set(qn("w:w"), str(w))
    for tr in rows:
        for tc, w in zip(tr.findall(qn("w:tc")), twips):
            tcw = tc.get_or_add_tcPr().find(qn("w:tcW"))
            if tcw is not None:
                tcw.set(qn("w:type"), "dxa")
                tcw.set(qn("w:w"), str(w))


def _apply_align(rows, aligns):
    for tr in rows:
        for tc, align in zip(tr.findall(qn("w:tc")), aligns):
            if align in ("left", "center", "right"):
                for p in tc.findall(qn("w:p")):
                    p.get_or_add_pPr().get_or_add_jc().set(qn("w:val"), align)


def _apply_colors(tbl, colors):
    for r in list(tbl.iter(qn("w:r"))):
        t = r.find(qn("w:t"))
        if t is None or not t.text or not any(c in t.text for c in colors):
            continue
        pieces, buf = [], ""
        for ch in t.text:
            if ch in colors:
                if buf:
                    pieces.append((buf, None))
                    buf = ""
                pieces.append((ch, colors[ch]))
            else:
                buf += ch
        if buf:
            pieces.append((buf, None))
        anchor = r
        for text, color in pieces:
            nr = deepcopy(r)
            nt = nr.find(qn("w:t"))
            nt.text = text
            nt.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            if color:
                nr.get_or_add_rPr().get_or_add_color().set(qn("w:val"), color)
            anchor.addnext(nr)
            anchor = nr
        r.getparent().remove(r)


@register
class OutputTables(Renderer):
    """Output tables: style, widths, alignment and symbol colours of the tables of {{output}}."""
    name = "output_tables"
    family = OUTPUT
    order = 50
    spec = SPEC

    def format_output(self, doc, inserted_elements, ctx):
        format_tables(doc, inserted_elements, ctx.props)
