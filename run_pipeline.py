#!/usr/bin/env python3
"""
Simplified script to run the knowledge graph pipeline
"""
import argparse
from main import KnowledgeGraphPipeline


def run_pipeline(args):
    """Run the pipeline with command line arguments"""
    pipeline = KnowledgeGraphPipeline(args.config)

    if args.mode == "build":
        success = pipeline.run_pipeline(
            input_file=args.input_file,
            clear_existing=args.clear
        )

        if success:
            print("✅ Pipeline completed successfully!")
        else:
            print("❌ Pipeline failed. Check logs for details.")

    elif args.mode == "query":
        pipeline.interactive_query()

    elif args.mode == "both":
        success = pipeline.run_pipeline(
            input_file=args.input_file,
            clear_existing=args.clear
        )

        if success:
            pipeline.interactive_query()

    pipeline.close()


def main():
    parser = argparse.ArgumentParser(description="Knowledge Graph Pipeline")
    parser.add_argument("--config", default="config/config.yaml", help="Configuration file")
    parser.add_argument("--input-file", default="data/raw_news.txt", help="Input text file")
    parser.add_argument("--clear", action="store_true", help="Clear existing graph data")
    parser.add_argument("--mode", choices=["build", "query", "both"], default="both",
                        help="Pipeline mode: build graph, query, or both")

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()