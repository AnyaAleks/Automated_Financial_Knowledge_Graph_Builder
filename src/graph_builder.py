import pandas as pd
import logging
from typing import Dict, List
from neo4j import GraphDatabase
import time

logger = logging.getLogger(__name__)


class Neo4jGraphBuilder:
    def __init__(self, config: Dict):
        self.config = config
        neo4j_config = config['neo4j']

        self.driver = GraphDatabase.driver(
            neo4j_config['uri'],
            auth=(neo4j_config['username'], neo4j_config['password'])
        )

        # Test connection
        self._test_connection()

    def _test_connection(self):
        """Test Neo4j connection"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                value = result.single()["test"]
                logger.info(f"Neo4j connection successful: {value}")
        except Exception as e:
            logger.error(f"Neo4j connection failed: {e}")
            raise

    def build_graph(self, df: pd.DataFrame, clear_existing: bool = False):
        """Build knowledge graph from DataFrame"""
        if df.empty:
            logger.warning("Empty DataFrame, nothing to build")
            return

        logger.info(f"Building graph from {len(df)} triplets")

        if clear_existing:
            self.clear_database()

        # Create constraints
        self._create_constraints()

        # Import data in batches
        batch_size = 100
        total_batches = (len(df) // batch_size) + 1

        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            self._import_batch(batch)

            batch_num = (i // batch_size) + 1
            logger.info(f"Imported batch {batch_num}/{total_batches} ({len(batch)} triplets)")

        logger.info("Graph construction complete")

    def clear_database(self):
        """Clear all nodes and relationships"""
        logger.info("Clearing existing database...")
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("Database cleared")

    def _create_constraints(self):
        """Create database constraints"""
        with self.driver.session() as session:
            # Create uniqueness constraint on entity name
            session.run("""
                CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) 
                REQUIRE e.name IS UNIQUE
            """)

            # Create indexes for faster querying
            session.run("CREATE INDEX IF NOT EXISTS FOR (c:Company) ON (c.name)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name)")
            session.run("CREATE INDEX IF NOT EXISTS FOR (pr:Product) ON (pr.name)")

            logger.info("Database constraints and indexes created")

    def _import_batch(self, batch: pd.DataFrame):
        """Import a batch of triplets"""
        query = """
        UNWIND $triplets AS triplet
        MERGE (head:Entity {name: triplet.head})
        SET head.type = triplet.head_type
        MERGE (tail:Entity {name: triplet.tail})
        SET tail.type = triplet.tail_type

        // Set specific labels based on type
        CALL apoc.create.addLabels(head, [head.type]) YIELD node AS headNode
        CALL apoc.create.addLabels(tail, [tail.type]) YIELD node AS tailNode

        // Create relationship
        MERGE (headNode)-[r:RELATION {type: triplet.relation}]->(tailNode)
        SET r.confidence = triplet.confidence,
            r.source = 'extracted',
            r.created = datetime()
        """

        # Prepare data for Neo4j
        triplets_data = []
        for _, row in batch.iterrows():
            triplet = {
                'head': row['head'],
                'tail': row['tail'],
                'relation': row['relation'],
                'head_type': row.get('head_type', 'ENTITY'),
                'tail_type': row.get('tail_type', 'ENTITY'),
                'confidence': float(row.get('confidence', 0.8))
            }
            triplets_data.append(triplet)

        try:
            with self.driver.session() as session:
                session.run(query, triplets=triplets_data)
        except Exception as e:
            logger.error(f"Error importing batch: {e}")

    def get_graph_stats(self) -> Dict:
        """Get graph statistics"""
        stats_query = """
        MATCH (n)
        RETURN 
            count(DISTINCT n) as total_nodes,
            count(DISTINCT labels(n)[0]) as unique_labels

        UNION ALL

        MATCH ()-[r]->()
        RETURN 
            count(DISTINCT r) as total_relationships,
            count(DISTINCT type(r)) as unique_relationship_types
        """

        with self.driver.session() as session:
            result = session.run(stats_query)
            stats = {}

            for record in result:
                for key, value in record.items():
                    stats[key] = value

        return stats

    def visualize_in_browser(self):
        """Provide instructions for visualization in Neo4j Browser"""
        uri = self.config['neo4j']['uri']
        logger.info(f"Graph visualization available at Neo4j Browser: {uri}")
        logger.info("Sample queries:")
        logger.info("  MATCH (n) RETURN n LIMIT 50")
        logger.info("  MATCH (c:Company)-[r]->(o) RETURN c, r, o LIMIT 25")

    def close(self):
        """Close Neo4j driver"""
        self.driver.close()


if __name__ == "__main__":
    # Test graph building
    config = {
        'neo4j': {
            'uri': 'bolt://localhost:7687',
            'username': 'neo4j',
            'password': 'password'
        }
    }

    # Sample data
    test_data = pd.DataFrame([
        {'head': 'Apple', 'relation': 'ACQUIRED', 'tail': 'DarwinAI', 'confidence': 0.95},
        {'head': 'Microsoft', 'relation': 'INVESTED_IN', 'tail': 'OpenAI', 'confidence': 0.92},
        {'head': 'Tesla', 'relation': 'LAUNCHED', 'tail': 'Model Y', 'confidence': 0.88},
    ])

    builder = Neo4jGraphBuilder(config)
    builder.build_graph(test_data)
    stats = builder.get_graph_stats()
    print(f"Graph stats: {stats}")
    builder.close()