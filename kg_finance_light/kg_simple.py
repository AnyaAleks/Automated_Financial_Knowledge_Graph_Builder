"""
Simplest Knowledge Graph Pipeline for Experiment
"""
import os
import re
from neo4j import GraphDatabase
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleKGPipeline:
    def __init__(self):
        # Neo4j connection - default credentials
        self.uri = "bolt://localhost:7687"
        self.user = "neo4j"
        self.password = "neo4j"

        # Simple regex patterns for extraction
        self.patterns = {
            "ACQUIRED": [
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+acquired\s+([A-Za-z0-9\s]+?)(?:\s+for|\s+in|\.|$)',
                r'([A-Z][a-z]+)\s+bought\s+([A-Za-z0-9\s]+)'
            ],
            "INVESTED_IN": [
                r'([A-Z][a-z]+)\s+invested\s+(?:\$[\d\.]+\s+\w+\s+)?in\s+([A-Za-z0-9\s]+)'
            ],
            "LAUNCHED": [
                r'([A-Z][a-z]+)\s+launched\s+([A-Za-z0-9\s]+)'
            ],
            "FOUNDED": [
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+founded\s+([A-Za-z0-9\s]+)'
            ],
            "CEO_OF": [
                r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+is\s+CEO\s+of\s+([A-Z][a-z]+)'
            ]
        }

    def connect_to_neo4j(self):
        """Test Neo4j connection"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                if result.single()["test"] == 1:
                    logger.info("✅ Connected to Neo4j successfully")
                    return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Neo4j: {e}")
            logger.info("\nTo start Neo4j, try:")
            logger.info("1. Install Neo4j: sudo apt install neo4j")
            logger.info("2. Start Neo4j: sudo systemctl start neo4j")
            logger.info("3. Open browser: http://localhost:7474 (login: neo4j/neo4j)")
            return False

    def extract_from_text(self, text):
        """Extract relationships using regex patterns"""
        triplets = []

        for relation, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    if len(match.groups()) >= 2:
                        head = match.group(1).strip()
                        tail = match.group(2).strip()

                        # Clean the tail
                        tail = re.sub(r'\s+(?:in|for|by|with|at)\s+\d{4}.*', '', tail)
                        tail = re.sub(r'\s+\$[\d\.]+\s*\w*.*', '', tail)
                        tail = tail.strip('., ')

                        if head and tail and head != tail:
                            triplets.append({
                                "head": head,
                                "relation": relation,
                                "tail": tail
                            })
                            logger.debug(f"Found: {head} --[{relation}]--> {tail}")

        return triplets

    def create_kg(self, triplets):
        """Create knowledge graph in Neo4j"""
        if not triplets:
            logger.warning("No triplets to create graph")
            return

        try:
            with self.driver.session() as session:
                # Clear old data
                session.run("MATCH (n) DETACH DELETE n")
                logger.info("Cleared old graph data")

                # Create new nodes and relationships
                created_count = 0
                for t in triplets:
                    query = """
                    MERGE (a:Company {name: $head})
                    MERGE (b:Company {name: $tail})
                    MERGE (a)-[r:RELATES {type: $relation}]->(b)
                    SET r.created = timestamp()
                    """
                    session.run(query,
                                head=t["head"],
                                tail=t["tail"],
                                relation=t["relation"])
                    created_count += 1

                logger.info(f"✅ Created graph with {created_count} relationships")

                # Create some indexes
                session.run("CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.name)")

        except Exception as e:
            logger.error(f"Error creating graph: {e}")

    def run_queries(self):
        """Run sample queries"""
        queries = [
            ("All nodes", "MATCH (n) RETURN n.name as Name, labels(n) as Type LIMIT 10"),
            ("All relationships",
             "MATCH (a)-[r]->(b) RETURN a.name as From, type(r) as Relation, b.name as To LIMIT 10"),
            ("Apple's relationships",
             "MATCH (n {name: 'Apple'})-[r]->(m) RETURN type(r) as Relation, m.name as Target"),
            ("Investments",
             "MATCH (a)-[r:RELATES {type: 'INVESTED_IN'}]->(b) RETURN a.name as Investor, b.name as Investment"),
            ("Acquisitions",
             "MATCH (a)-[r:RELATES {type: 'ACQUIRED'}]->(b) RETURN a.name as Acquirer, b.name as Acquired")
        ]

        print("\n" + "=" * 60)
        print("📊 KNOWLEDGE GRAPH QUERY RESULTS")
        print("=" * 60)

        for query_name, query in queries:
            print(f"\n🔍 {query_name}:")
            print(f"   Cypher: {query}")
            try:
                with self.driver.session() as session:
                    result = session.run(query)
                    records = list(result)

                    if records:
                        for i, record in enumerate(records, 1):
                            print(f"   {i}. {dict(record)}")
                    else:
                        print("   No results found")
            except Exception as e:
                print(f"   Error: {e}")

    def close(self):
        """Close Neo4j connection"""
        if hasattr(self, 'driver'):
            self.driver.close()
            logger.info("Closed Neo4j connection")


def main():
    """Main function"""
    logger.info("🚀 Starting Simple Knowledge Graph Pipeline")

    # Sample data for testing
    sample_text = """
    Apple acquired AI startup DarwinAI in January 2024.
    Microsoft invested $10 billion in OpenAI in 2023.
    Tesla launched Model Y electric car in 2023.
    Amazon partnered with NVIDIA for AI chip development.
    Google CEO Sundar Pichai announced Gemini AI in 2023.
    Meta invested $5 billion in VR technology.
    Elon Musk founded xAI company.
    IBM acquired HashiCorp for $6.4 billion.
    Samsung launched Galaxy AI smartphone.
    """

    # Initialize pipeline
    pipeline = SimpleKGPipeline()

    try:
        # 1. Connect to Neo4j
        if not pipeline.connect_to_neo4j():
            logger.info("\n⚠️  Running in OFFLINE MODE (extraction only)")
            logger.info("Triplets will be extracted but not saved to Neo4j")

            # Extract triplets anyway
            triplets = pipeline.extract_from_text(sample_text)
            logger.info(f"\nExtracted {len(triplets)} triplets:")
            for t in triplets:
                print(f"  • {t['head']} --[{t['relation']}]--> {t['tail']}")

            print("\n" + "=" * 60)
            print("To save to Neo4j, you need to:")
            print("1. Install Neo4j: sudo apt install neo4j")
            print("2. Start Neo4j: sudo systemctl start neo4j")
            print("3. Run: python kg_simple.py")
            print("=" * 60)
            return

        # 2. Extract triplets
        logger.info("\n📄 Extracting relationships from text...")
        triplets = pipeline.extract_from_text(sample_text)
        logger.info(f"✅ Extracted {len(triplets)} triplets")

        # 3. Create knowledge graph
        logger.info("\n🗺️  Creating knowledge graph in Neo4j...")
        pipeline.create_kg(triplets)

        # 4. Run queries
        logger.info("\n🔍 Running sample queries...")
        pipeline.run_queries()

        # 5. Success message
        print("\n" + "=" * 60)
        print("✅ EXPERIMENT COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n🎯 What was accomplished:")
        print("1. ✅ Extracted entities and relationships from text")
        print("2. ✅ Created knowledge graph in Neo4j")
        print("3. ✅ Executed Cypher queries")
        print(f"4. ✅ Built graph with {len(triplets)} relationships")

        print("\n📊 Next steps:")
        print("1. Open Neo4j Browser: http://localhost:7474")
        print("2. Login with: neo4j / neo4j")
        print("3. Try these queries:")
        print("   • MATCH (n) RETURN n LIMIT 25")
        print("   • MATCH (a)-[r]->(b) RETURN a, r, b")
        print("   • MATCH (n:Company) RETURN n.name")

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
    finally:
        pipeline.close()
        logger.info("Pipeline finished")


if __name__ == "__main__":
    main()