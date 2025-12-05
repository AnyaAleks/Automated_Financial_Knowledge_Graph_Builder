"""
Main pipeline for automated knowledge graph construction
"""
import os
import sys
import yaml
import logging
from dotenv import load_dotenv
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / "src"))

from preprocess import TextPreprocessor
from extract import EntityRelationshipExtractor
from clean import DataCleaner
from graph_builder import Neo4jGraphBuilder
from query_nl import NaturalLanguageQuery

# Load environment variables
load_dotenv()


class KnowledgeGraphPipeline:
    def __init__(self, config_path: str = "config/config.yaml"):
        """Initialize pipeline with configuration"""
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Substitute environment variables
        self._substitute_env_vars()

        # Setup logging
        self._setup_logging()

        # Initialize components
        self.preprocessor = TextPreprocessor(self.config)
        self.extractor = EntityRelationshipExtractor(self.config)
        self.cleaner = DataCleaner(self.config)
        self.graph_builder = Neo4jGraphBuilder(self.config)
        self.query_engine = NaturalLanguageQuery(self.config)

        logger = logging.getLogger(__name__)
        logger.info("Knowledge Graph Pipeline initialized")

    def _substitute_env_vars(self):
        """Substitute environment variables in config"""

        def replace_env_vars(obj):
            if isinstance(obj, str) and obj.startswith('${') and obj.endswith('}'):
                env_var = obj[2:-1]
                return os.getenv(env_var, obj)
            elif isinstance(obj, dict):
                return {k: replace_env_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_env_vars(item) for item in obj]
            else:
                return obj

        self.config = replace_env_vars(self.config)

    def _setup_logging(self):
        """Configure logging"""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('file', 'kg_pipeline.log')

        logging.basicConfig(
            level=log_level,
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )

    def run_pipeline(self, input_file: str, clear_existing: bool = False):
        """Run complete pipeline"""
        logger = logging.getLogger(__name__)
        logger.info("Starting Knowledge Graph Pipeline")

        try:
            # Step 1: Preprocessing
            logger.info("Step 1: Text Preprocessing")
            sentences = self.preprocessor.preprocess_file(input_file)

            if not sentences:
                logger.error("No sentences extracted from input file")
                return False

            # Step 2: Entity and Relationship Extraction
            logger.info("Step 2: Entity and Relationship Extraction")
            all_triplets = []

            for i, sentence in enumerate(sentences):
                logger.debug(f"Processing sentence {i + 1}/{len(sentences)}")
                triplets = self.extractor.extract_from_text(sentence)
                all_triplets.extend(triplets)

            logger.info(f"Extracted {len(all_triplets)} triplets from {len(sentences)} sentences")

            # Step 3: Data Cleaning
            logger.info("Step 3: Data Cleaning and Standardization")
            cleaned_df = self.cleaner.clean_triplets(all_triplets)

            if cleaned_df.empty:
                logger.error("No valid triplets after cleaning")
                return False

            # Save cleaned data
            output_dir = Path("data")
            output_dir.mkdir(exist_ok=True)

            cleaned_csv = output_dir / "cleaned_triplets.csv"
            cleaned_df.to_csv(cleaned_csv, index=False)
            logger.info(f"Cleaned data saved to {cleaned_csv}")

            # Step 4: Graph Construction
            logger.info("Step 4: Graph Construction in Neo4j")
            self.graph_builder.build_graph(cleaned_df, clear_existing=clear_existing)

            # Get graph statistics
            stats = self.graph_builder.get_graph_stats()
            logger.info(f"Graph Statistics: {stats}")

            # Step 5: Sample Queries
            logger.info("Step 5: Testing Natural Language Queries")
            sample_questions = [
                "What companies were acquired?",
                "Who invested in AI companies?",
                "What products were launched recently?"
            ]

            for question in sample_questions:
                results = self.query_engine.ask_question(question)
                logger.info(f"Question: {question}")
                logger.info(f"Results: {len(results)} records found")

            logger.info("Pipeline completed successfully!")
            return True

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return False

    def interactive_query(self):
        """Interactive query interface"""
        logger = logging.getLogger(__name__)
        logger.info("Starting interactive query mode")

        print("\n" + "=" * 50)
        print("Knowledge Graph Query Interface")
        print("=" * 50)
        print("Type 'exit' to quit\n")

        while True:
            try:
                question = input("\nEnter your question: ").strip()

                if question.lower() in ['exit', 'quit', 'q']:
                    break

                if not question:
                    continue

                # Execute query
                results = self.query_engine.ask_question(question)

                if not results:
                    print("No results found.")
                    continue

                # Display results
                print(f"\nFound {len(results)} result(s):")
                print("-" * 40)

                for i, record in enumerate(results, 1):
                    print(f"\nResult {i}:")
                    for key, value in record.items():
                        print(f"  {key}: {value}")

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Query error: {e}")
                print(f"Error: {e}")

        print("\nGoodbye!")

    def close(self):
        """Cleanup resources"""
        self.graph_builder.close()
        self.query_engine.close()
        logger = logging.getLogger(__name__)
        logger.info("Pipeline resources cleaned up")


def main():
    """Main entry point"""
    # Create sample data if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    sample_file = data_dir / "raw_news.txt"
    if not sample_file.exists():
        sample_text = """Apple acquired AI startup DarwinAI in January 2024 for approximately $100 million. The acquisition aims to enhance Apple's on-device AI capabilities.

Microsoft invested $10 billion in OpenAI in 2023, strengthening their partnership in artificial intelligence development. This investment gives Microsoft exclusive cloud computing rights for OpenAI.

Tesla launched its new electric vehicle Model Y in 2023, featuring advanced autonomous driving capabilities. The Model Y has become one of the best-selling electric vehicles worldwide.

Amazon partnered with NVIDIA to develop next-generation AI chips for cloud computing. The partnership aims to create more efficient AI hardware for Amazon Web Services.

Google's CEO Sundar Pichai announced the launch of Gemini AI in December 2023. Gemini is Google's most advanced AI model to date, competing with OpenAI's GPT-4.

Meta invested $5 billion in virtual reality technology in 2023, focusing on metaverse development. The investment includes research into AR glasses and VR headsets.

NVIDIA's stock price surged after reporting record revenue from AI chip sales. The company's market capitalization exceeded $1 trillion in 2023.

Elon Musk founded xAI in 2023, a new artificial intelligence company aimed at understanding the true nature of the universe. xAI has recruited researchers from DeepMind and OpenAI.

IBM acquired HashiCorp for $6.4 billion in 2024 to enhance its hybrid cloud offerings. This acquisition strengthens IBM's position in infrastructure automation software.

Samsung launched the Galaxy AI smartphone series in January 2024, featuring on-device AI capabilities. The phones include real-time language translation and advanced photo editing."""

        with open(sample_file, 'w') as f:
            f.write(sample_text)
        print(f"Created sample data file: {sample_file}")

    # Initialize and run pipeline
    pipeline = KnowledgeGraphPipeline()

    try:
        # Run the pipeline
        success = pipeline.run_pipeline(
            input_file=str(sample_file),
            clear_existing=True  # Clear existing graph data
        )

        if success:
            # Start interactive query mode
            pipeline.interactive_query()
        else:
            print("Pipeline failed. Check logs for details.")

    except KeyboardInterrupt:
        print("\nPipeline interrupted by user")
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()