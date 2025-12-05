import re
import logging
from typing import List, Dict
import nltk
from nltk.tokenize import sent_tokenize

# Download NLTK data (first time only)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

logger = logging.getLogger(__name__)


class TextPreprocessor:
    def __init__(self, config: Dict):
        self.config = config
        self.max_sentences = config['pipeline']['max_sentences']

    def preprocess_file(self, file_path: str) -> List[str]:
        """Read and preprocess text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            logger.info(f"Loaded text from {file_path}, length: {len(text)} chars")
            return self.preprocess_text(text)

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []

    def preprocess_text(self, text: str) -> List[str]:
        """Clean and split text into sentences"""
        # Clean text
        text = self._clean_text(text)

        # Split into sentences
        sentences = sent_tokenize(text)

        # Filter and limit sentences
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        sentences = sentences[:self.max_sentences]

        logger.info(f"Preprocessed text into {len(sentences)} sentences")
        return sentences

    def _clean_text(self, text: str) -> str:
        """Clean text by removing unwanted characters"""
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)

        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?-]', ' ', text)

        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)

        # Remove extra whitespace
        text = text.strip()

        return text

    def batch_sentences(self, sentences: List[str], batch_size: int = None) -> List[List[str]]:
        """Batch sentences for processing"""
        if batch_size is None:
            batch_size = self.config['pipeline']['batch_size']

        batches = []
        for i in range(0, len(sentences), batch_size):
            batches.append(sentences[i:i + batch_size])

        return batches


if __name__ == "__main__":
    # Example usage
    config = {
        'pipeline': {
            'max_sentences': 100,
            'batch_size': 10
        }
    }

    preprocessor = TextPreprocessor(config)
    test_text = "Apple acquired DarwinAI. Microsoft invested in OpenAI. Tesla launched new car."
    sentences = preprocessor.preprocess_text(test_text)
    print(f"Processed {len(sentences)} sentences")