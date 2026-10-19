# DOCX templates of the LinTO catalog

`templates/default/linto-*.docx` are generated, never edited by hand:

```bash
uv pip install python-docx pillow lxml
python scripts/templates/compte_rendu.py        # -> templates/default/linto-compte-rendu.docx
python scripts/templates/tableau_de_suivi.py
python scripts/templates/brief_commercial.py
python scripts/templates/note_technique.py
python scripts/templates/points_cles.py
python scripts/templates/check_docx.py templates/default/linto-compte-rendu.docx   # element order Word requires
```

- `docx_kit.py`: shared building blocks (A4 document, header and footer, infographic `Card`: tiles, panels,
  repeated rows). Fonts from `templates/assets/fonts/` (Inter, SIL Open Font License) are embedded, so documents
  render the same in Word and in the LibreOffice used for PDF export.
- Each builder documents its placeholders `{{name: instruction}}`: the instruction is what the extraction
  prompt reads, and it points to a section of the service output. See `docs/TEMPLATE_RENDERERS.md` for
  repeated rows (`{{list.field}}`), rich values, mind maps and output tables.
- Constraints of the renderer: placeholders only in top-level tables of the body (no nested tables, no
  tables in header or footer), one Word run per placeholder, no `}` inside an instruction.
