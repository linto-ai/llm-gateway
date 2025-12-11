#!/usr/bin/env python3
"""Document generation service for DOCX/PDF export."""
import json
import logging
import subprocess
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any

from app.models.document_template import DocumentTemplate
from app.models.job import Job

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for generating documents from templates and job results."""

    TEMPLATES_DIR = Path("/var/www/data/templates")
    # Default template location - used when no template is provided
    DEFAULT_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates/default/basic-report.docx"

    # Standard placeholders always available
    STANDARD_PLACEHOLDERS = [
        "output",
        "job_id",
        "job_date",
        "service_name",
        "flavor_name",
        "organization_name",
        "generated_at",
    ]

    @staticmethod
    def _clean_trailing_backslashes(content: str) -> str:
        """
        Remove trailing backslashes at end of lines.

        LLMs sometimes add backslashes for line breaks in markdown,
        but these are not needed when using nl2br extension.
        """
        if not content:
            return content
        import re
        # Remove single backslash at end of lines (but keep escaped backslashes \\)
        return re.sub(r'(?<!\\)\\(?=\n|$)', '', content)

    async def generate_docx(
        self,
        job: Job,
        template: Optional[DocumentTemplate] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        version_content: Optional[str] = None,
        version_metadata: Optional[Dict[str, Any]] = None,
    ) -> BytesIO:
        """
        Generate DOCX from template with placeholder substitution.

        Args:
            job: Job with result data
            template: Optional document template to use (uses default if not provided)
            custom_fields: Optional additional fields
            version_content: Optional content from a specific version (overrides job.result)
            version_metadata: Optional metadata from a specific version (overrides job.result.extracted_metadata)

        Returns:
            BytesIO containing the generated DOCX
        """
        try:
            from docx import Document
        except ImportError:
            raise ImportError("python-docx is required for document generation")

        # Determine template path
        if template:
            template_path = self.TEMPLATES_DIR / template.file_path
        else:
            # Use built-in default template
            template_path = self.DEFAULT_TEMPLATE_PATH
            if not template_path.exists():
                raise RuntimeError(f"Default template not found at {template_path}")

        doc = Document(template_path)

        placeholders = self.get_placeholders(job, custom_fields, version_content=version_content, version_metadata=version_metadata)
        self.substitute_placeholders(doc, placeholders)

        output = BytesIO()
        doc.save(output)
        output.seek(0)
        return output

    async def generate_pdf(
        self,
        job: Job,
        template: Optional[DocumentTemplate] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        version_content: Optional[str] = None,
        version_metadata: Optional[Dict[str, Any]] = None,
    ) -> BytesIO:
        """
        Generate PDF from job result.

        Always uses: DOCX -> LibreOffice -> PDF pipeline.

        Args:
            job: Job with result data
            template: Optional document template (uses default if not provided)
            custom_fields: Optional additional fields
            version_content: Optional content from a specific version (overrides job.result)
            version_metadata: Optional metadata from a specific version (overrides job.result.extracted_metadata)

        Returns:
            BytesIO containing the generated PDF
        """
        # Generate DOCX first (handles default template)
        docx_buffer = await self.generate_docx(job, template, custom_fields, version_content=version_content, version_metadata=version_metadata)

        # Convert via LibreOffice
        return await self._convert_docx_to_pdf(docx_buffer, job)

    async def generate_html(
        self,
        job: Job,
        template: Optional[DocumentTemplate] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        version_content: Optional[str] = None,
        version_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate HTML preview from job result using mammoth.

        Pipeline: DOCX template → placeholder substitution → mammoth → HTML

        This preserves:
        - Text formatting (bold, italic, headings)
        - Images (embedded as base64)
        - Tables
        - Lists

        Note: Complex layouts (columns, headers/footers) may be simplified.

        Args:
            job: Job with result data
            template: Optional document template (uses default if not provided)
            custom_fields: Optional additional fields
            version_content: Optional content from a specific version (overrides job.result)
            version_metadata: Optional metadata from a specific version (overrides job.result.extracted_metadata)

        Returns:
            HTML string with embedded images
        """
        try:
            import mammoth
        except ImportError:
            raise ImportError("mammoth is required for HTML preview generation")

        # Generate DOCX first (reuse existing logic)
        docx_buffer = await self.generate_docx(job, template, custom_fields, version_content=version_content, version_metadata=version_metadata)

        # Convert DOCX to HTML using mammoth
        result = mammoth.convert_to_html(docx_buffer)
        html_content = result.value

        # Log any conversion warnings
        if result.messages:
            for msg in result.messages:
                logger.warning(f"mammoth conversion warning: {msg}")

        # Wrap in a basic HTML structure with styling
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            color: #222;
        }}
        h1 {{ font-size: 1.8em; border-bottom: 2px solid #eee; padding-bottom: 0.3em; }}
        h2 {{ font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.2em; }}
        p {{ margin: 0.8em 0; }}
        ul, ol {{ margin: 0.8em 0; padding-left: 2em; }}
        li {{ margin: 0.3em 0; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background-color: #f5f5f5;
            font-weight: 600;
        }}
        tr:nth-child(even) {{
            background-color: #fafafa;
        }}
        img {{
            max-width: 100%;
            height: auto;
        }}
        blockquote {{
            border-left: 4px solid #ddd;
            margin: 1em 0;
            padding-left: 1em;
            color: #666;
        }}
        code {{
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }}
        pre {{
            background: #f5f5f5;
            padding: 1em;
            border-radius: 5px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

        return html

    async def _convert_docx_to_pdf(self, docx_buffer: BytesIO, job: Job) -> BytesIO:
        """Convert DOCX buffer to PDF using LibreOffice."""
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = Path(tmpdir) / "document.docx"
            pdf_path = Path(tmpdir) / "document.pdf"

            with open(docx_path, 'wb') as f:
                f.write(docx_buffer.getvalue())

            # LibreOffice conversion
            try:
                subprocess.run(
                    [
                        'libreoffice',
                        '--headless',
                        '--convert-to', 'pdf',
                        '--outdir', tmpdir,
                        str(docx_path)
                    ],
                    check=True,
                    capture_output=True,
                    timeout=60  # 60 second timeout
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"LibreOffice conversion failed: {e.stderr.decode()}")
                raise RuntimeError("PDF conversion failed")
            except FileNotFoundError:
                raise RuntimeError("LibreOffice not installed. PDF export unavailable.")
            except subprocess.TimeoutExpired:
                raise RuntimeError("PDF conversion timed out")

            # Read the generated PDF
            if not pdf_path.exists():
                raise RuntimeError("PDF file was not generated")

            with open(pdf_path, 'rb') as f:
                return BytesIO(f.read())

    def get_placeholders(
        self,
        job: Job,
        custom_fields: Optional[Dict[str, Any]] = None,
        version_content: Optional[str] = None,
        version_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get all available placeholders for template substitution.

        Args:
            job: Job with result data
            custom_fields: Optional additional fields
            version_content: Optional content from a specific version (overrides job.result)
            version_metadata: Optional metadata from a specific version (overrides job.result.extracted_metadata)

        Returns:
            Dict mapping placeholder names to values
        """
        # Use version_content if provided, otherwise extract from job result
        output_content = version_content if version_content else self._get_result_content(job)

        placeholders = {
            # Standard placeholders
            "output": output_content,
            "job_id": str(job.id),
            "job_date": job.completed_at.strftime("%Y-%m-%d") if job.completed_at else "",
            "service_name": job.service.name if job.service else "",
            "flavor_name": job.flavor.name if job.flavor else "",
            "organization_name": job.organization_id or "",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

        # Add extracted metadata fields - use version_metadata if provided, else job.result.extracted_metadata
        extracted_metadata = version_metadata
        if extracted_metadata is None and job.result and isinstance(job.result, dict):
            extracted_metadata = job.result.get('extracted_metadata')

        if extracted_metadata and isinstance(extracted_metadata, dict):
            for key, value in extracted_metadata.items():
                if key.startswith("_"):  # Skip internal fields like _extraction_error
                    continue
                # Don't override standard placeholders with metadata values
                if key in self.STANDARD_PLACEHOLDERS:
                    continue
                if isinstance(value, list):
                    # Format list items appropriately
                    if all(isinstance(v, dict) for v in value):
                        # List of dicts (like action_items with task/assignee)
                        formatted = []
                        for v in value:
                            if isinstance(v, dict):
                                formatted.append(" - ".join(str(x) for x in v.values()))
                            else:
                                formatted.append(str(v))
                        placeholders[key] = "\n".join(formatted)
                    else:
                        placeholders[key] = ", ".join(str(v) for v in value)
                else:
                    placeholders[key] = str(value) if value is not None else ""

        # Add custom fields (override if same name)
        if custom_fields:
            placeholders.update(custom_fields)

        return placeholders

    def substitute_placeholders(self, doc, placeholders: Dict[str, Any]) -> None:
        """
        Replace {{placeholder}} in DOCX paragraphs, tables, headers, footers.
        For {{output}} placeholder, convert markdown to proper DOCX formatting.

        Args:
            doc: python-docx Document object
            placeholders: Dict of placeholder values
        """
        output_content = placeholders.get("output", "")

        def replace_text_simple(text: str) -> str:
            """Replace placeholders except output (handled specially).

            Handles both formats:
            - {{key}} -> simple placeholder
            - {{key: description}} -> placeholder with extraction hint
            """
            import re
            for key, value in placeholders.items():
                if key == "output":
                    continue  # Handle output separately
                # Replace exact match {{key}}
                text = text.replace(f"{{{{{key}}}}}", str(value or ""))
                # Replace {{key: anything}} pattern (placeholder with description)
                pattern = r'\{\{' + re.escape(key) + r':[^}]*\}\}'
                text = re.sub(pattern, str(value or ""), text)
            return text

        def process_paragraph_for_output(para):
            """Check if paragraph contains {{output}} and replace with formatted content."""
            full_text = "".join(run.text for run in para.runs)
            if "{{output}}" in full_text:
                # Clear the paragraph
                for run in para.runs:
                    run.text = ""
                # Insert formatted markdown content after this paragraph
                return True
            return False

        # First pass: replace simple placeholders
        for para in doc.paragraphs:
            for run in para.runs:
                run.text = replace_text_simple(run.text)

        # Second pass: find and replace {{output}} with formatted content
        paragraphs_to_process = []
        for i, para in enumerate(doc.paragraphs):
            full_text = "".join(run.text for run in para.runs)
            if "{{output}}" in full_text:
                paragraphs_to_process.append((i, para))

        # Insert formatted content for each {{output}} placeholder
        for idx, para in paragraphs_to_process:
            # Clear the placeholder
            for run in para.runs:
                run.text = run.text.replace("{{output}}", "")
            # Insert markdown as formatted DOCX content
            self._insert_markdown_content(doc, para, output_content)

        # Replace in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for run in para.runs:
                            run.text = replace_text_simple(run.text)
                            # For tables, just use plain text for output
                            run.text = run.text.replace("{{output}}", output_content)

        # Replace in headers/footers (simple replacement only)
        for section in doc.sections:
            if section.header:
                for para in section.header.paragraphs:
                    for run in para.runs:
                        run.text = replace_text_simple(run.text)
            if section.footer:
                for para in section.footer.paragraphs:
                    for run in para.runs:
                        run.text = replace_text_simple(run.text)

        # Final pass: clean up any remaining unfilled placeholders
        # Matches {{anything}} or {{anything: with hint}}
        import re
        unfilled_pattern = r'\{\{[^}]+\}\}'

        def clean_unfilled(text: str) -> str:
            return re.sub(unfilled_pattern, '', text)

        for para in doc.paragraphs:
            for run in para.runs:
                run.text = clean_unfilled(run.text)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        for run in para.runs:
                            run.text = clean_unfilled(run.text)

        for section in doc.sections:
            if section.header:
                for para in section.header.paragraphs:
                    for run in para.runs:
                        run.text = clean_unfilled(run.text)
            if section.footer:
                for para in section.footer.paragraphs:
                    for run in para.runs:
                        run.text = clean_unfilled(run.text)

    def _insert_markdown_content(self, doc, after_para, markdown_content: str) -> None:
        """
        Convert markdown to DOCX formatting and insert after the given paragraph.

        Args:
            doc: python-docx Document object
            after_para: Paragraph to insert content after
            markdown_content: Markdown text to convert
        """
        try:
            from htmldocx import HtmlToDocx
            import markdown
            from copy import deepcopy
        except ImportError:
            # Fallback: just add plain text
            after_para.add_run(markdown_content)
            return

        # Clean trailing backslashes before conversion
        cleaned_content = self._clean_trailing_backslashes(markdown_content)

        # Convert markdown to HTML
        html_content = markdown.markdown(
            cleaned_content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )

        # Wrap in proper HTML structure
        html_doc = f"<html><body>{html_content}</body></html>"

        # Create a temporary document to convert HTML
        from docx import Document as DocxDocument
        temp_doc = DocxDocument()
        parser = HtmlToDocx()
        parser.add_html_to_document(html_doc, temp_doc)

        # Insert each element from temp_doc after the placeholder paragraph
        para_element = after_para._element
        insert_point = para_element
        for element in temp_doc.element.body:
            # Skip section properties (sectPr)
            if element.tag.endswith('sectPr'):
                continue
            # Deep copy the element to preserve all attributes and children
            new_element = deepcopy(element)
            insert_point.addnext(new_element)
            insert_point = new_element

    def _get_result_content(self, job: Job) -> str:
        """Extract text content from job result."""
        if not job.result:
            return ""
        if isinstance(job.result, str):
            return job.result
        elif isinstance(job.result, dict):
            return (
                job.result.get("content")
                or job.result.get("text")
                or job.result.get("output")
                or json.dumps(job.result, indent=2, ensure_ascii=False)
            )
        return str(job.result)

    def get_all_available_placeholders(
        self,
        template: Optional[DocumentTemplate] = None,
        extracted_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, list]:
        """
        Get all available placeholder categories.

        Returns:
            Dict with 'standard', 'template', and 'metadata' keys
        """
        result = {
            "standard": self.STANDARD_PLACEHOLDERS.copy(),
            "template": [],
            "metadata": [],
        }

        if template and template.placeholders:
            result["template"] = template.placeholders

        if extracted_metadata:
            result["metadata"] = [
                k for k in extracted_metadata.keys()
                if not k.startswith("_")
            ]

        return result


# Singleton instance
document_service = DocumentService()
