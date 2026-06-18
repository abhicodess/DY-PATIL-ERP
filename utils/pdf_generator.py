import os
import subprocess
import shutil
import logging
from flask import render_template, current_app
from weasyprint import HTML
from PyPDF2 import PdfMerger

logger = logging.getLogger("reports_engine")

class ReportGenerationError(Exception):
    def __init__(self, template_name, message):
        super().__init__(f"Failed to generate PDF from template '{template_name}': {message}")
        self.template_name = template_name

def generate_pdf(template_name, context, output_path):
    """
    Renders a Jinja2 template with context and converts it to a PDF using WeasyPrint.
    Ensures a Flask app context is active.
    """
    ctx = None
    try:
        # Check if we are running within a Flask application context
        if not current_app:
            from app import create_app
            flask_app = create_app()
            ctx = flask_app.app_context()
            ctx.push()
            
        html = render_template(template_name, **context)
        
        # Use static folder as base URL for absolute paths to images/styles
        base_url = current_app.static_folder if current_app else None
        
        HTML(string=html, base_url=base_url).write_pdf(output_path)
        logger.info(f"Successfully generated PDF: {output_path}")
        
    except Exception as e:
        logger.error(f"WeasyPrint compilation failed for {template_name}: {str(e)}", exc_info=True)
        raise ReportGenerationError(template_name, str(e))
    finally:
        if ctx:
            ctx.pop()

def compress_pdf(input_path, output_path):
    """
    Compresses a PDF file using Ghostscript's pdfwrite device.
    Falls back to copying the file directly if Ghostscript is not available.
    """
    try:
        cmd = [
            "gs",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",  # Balanced compression and readability
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={output_path}",
            input_path
        ]
        
        # Run subprocess and wait for completion
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        logger.info(f"Successfully compressed PDF: {input_path} -> {output_path}")
        return True
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning(f"Ghostscript compression failed/not available. Copying raw PDF: {e}")
        try:
            shutil.copyfile(input_path, output_path)
            return True
        except Exception as copy_err:
            logger.error(f"Raw PDF copy fallback failed: {copy_err}")
            return False

def merge_pdfs(paths_list, output_path):
    """
    Merges multiple PDF files into a single PDF document using PyPDF2.
    """
    try:
        merger = PdfMerger()
        for path in paths_list:
            if os.path.exists(path):
                merger.append(path)
            else:
                logger.warning(f"PDF merge path does not exist, skipping: {path}")
                
        merger.write(output_path)
        merger.close()
        logger.info(f"Successfully merged {len(paths_list)} PDFs into {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to merge PDFs: {str(e)}", exc_info=True)
        raise ReportGenerationError("merge_pdfs", str(e))
