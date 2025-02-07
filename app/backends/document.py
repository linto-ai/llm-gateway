from pydantic import BaseModel
import asyncio
import jinja2
from  typing import List, Sequence
from pathlib import Path
import os

import logging

from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
import re
from conf import cfg_instance

# Load configuration
cfg = cfg_instance(cfg_name="config")
semantic_chunker = SemanticChunker(HuggingFaceEmbeddings(model_name = "sentence-transformers/all-mpnet-base-v2"), min_chunk_size=cfg.document.min_chunk_size)
class Chapter(BaseModel):
    title: str
    content: str

class DocGenerator:
    def __init__(self, task_data, llm_adapter) -> None:
        self.document_config = task_data['backendParams']["document"]
        self.llm_adapter = llm_adapter
        self.chunker = semantic_chunker
        self.template_path = self.document_config["template_path"]
        self.template_file = Path(self.template_path).name
        self.max_sentences_title_generation = self.document_config["max_sentences_title_generation"]
        self.semaphore = asyncio.Semaphore(cfg.semaphore.max_concurrent_inferences)
        self.logger = logging.getLogger("DocGenerator")
        # System prompts
        self.load_prompts(task_data)

    def load_prompts(self, task_data):
        """
        Loads the title generation prompts from text files.
        """

        # Construct path to the prompt text files from task config
        doc_title_prompt_path = self.document_config["doc_title_prompt"]
        paragraph_title_prompt_path = self.document_config["paragraph_title_prompt"]
        try:
            with open(doc_title_prompt_path, 'r') as f:
                # Prevent file system caching
                os.fsync(f.fileno())
                self.doc_title_prompt = f.read()
            with open(paragraph_title_prompt_path, 'r') as f:
                # Prevent file system caching
                os.fsync(f.fileno())
                self.paragraph_title_prompt = f.read()
        except Exception as e:
            self.logger.error(f"Error loading title generation prompts: {e}")
            raise e

    def split_summary_into_paragraphs(self, summary):
        """
        Splits the provided summary text into paragraphs.
        Args:
            summary (str): The summary text to be split into paragraphs.
        Returns:
            list: A list of paragraphs obtained from the summary text.
        """

        return self.chunker.split_text(summary)


    async def create_chapters(self, paragraphs: List[str]) -> List:
        """
        Asynchronously creates chapters from a list of paragraphs.
        This method processes each paragraph, generates a title using the first max_sentences_title_generation sentences,
        and creates a Chapter object with the generated title and the paragraph content.
        Args:
            paragraphs (List[str]): A list of paragraphs to be converted into chapters.
        Returns:
            Sequence[Chapter]: A sequence of Chapter objects created from the paragraphs.
        """

        chapters: List[Chapter] = []

        # Process each paragraph
        async def process_paragraph(paragraph: str):
            async with self.semaphore:
                sentences = re.split(self.chunker.sentence_split_regex, paragraph)[:self.max_sentences_title_generation]
                title = await self.llm_adapter.async_publish(' '.join(sentences), system_prompt=self.paragraph_title_prompt, temperature=0.5, max_tokens=20)
                return Chapter(title=title, content=paragraph)
        
        tasks = [process_paragraph(paragraph) for paragraph in paragraphs]

        # Generate chapters
        chapters = await asyncio.gather(*tasks)

        # Generate document title based on chapter titles
        chapter_titles = [chapter.title for chapter in chapters]
        title = await self.llm_adapter.async_publish('\n'.join(chapter_titles), system_prompt=self.doc_title_prompt, temperature=0.5, max_tokens=20)
        return title, chapters
    

    def render_document(self, title: str, chapters: Sequence[Chapter]) -> str:
        """
        Renders a document using a Jinja template.
        Args:
            title (str): The title of the document.
            chapters (Sequence[Chapter]): A sequence of Chapter objects to be included in the document.
        Returns:
            str: The rendered document as a string.
        """

        chapters_to_render = [
            {
                "title": chapter.title,
                "paragraph": chapter.content,
            }
            for chapter in chapters if chapter.content
        ]

        # Load Jinja template
        current_dir = Path(self.template_path).parent
        jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(current_dir))
        template = jinja_environment.get_template(self.template_file)

        # Render template
        rendered = template.render(
            title=title,
            chapters=chapters_to_render,
        )

        return rendered
    
    def run(self, summary: str) -> List[Chapter]:
        """
        Pipeline to split a summary into paragraphs and segment it into chapters then output a markdown document.
        Args:
            summary (str): The input summary to process.
        Returns:
            List[Chapter]: A list of segmented chapters.
        """
        self.logger.info(f"Running document generation")

        # Split summary into paragraphs
        paragraphs = self.split_summary_into_paragraphs(summary)

        # Create chapters
        title, chapters =  asyncio.run(self.create_chapters(paragraphs))

        # Render document
        return self.render_document(title, chapters)

#TODO add min_chunk_size to the config and using in the semantic split 