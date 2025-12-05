#!/usr/bin/env python3
"""
Simple Knowledge Graph Pipeline with Neo4j
"""
import os
import re
import pandas as pd
from neo4j import GraphDatabase
import spacy
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleKG:
    def __init__(self):
        # Neo4j connection
        self.uri = "bolt://localhost:7687"
        self.user = "neo4j"
        self.password = "neo4j"
        
        # Load spaCy model
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✅ spaCy model loaded")
        except:
            logger.error("❌ spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            raise
        
        # Connect to Neo4j
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        
    def extract_entities(self, text):
        """Extract entities using spaCy"""
        doc = self.nlp(text)
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
        return entities
    
    def extract_relations(self, text):
        """Extract relations using regex patterns"""
        patterns = {
            "ACQUIRED": r'(\w+(?:\s+\w+)*)\s+(?:acquired|bought|purchased)\s+([\w\s]+)',
            "INVESTED_IN": r'(\w+)\s+invested\s+(?:\$\d+(?:\s+\w+)*\s+)?in\s+([\w\s]+)',
            "LAUNCHED": r'(\w+)\s+launched\s+([\w\s]+)',
            "CEO_OF": r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+is\s+(?:the\s+)?CEO\s+of\s+(\w+)',
            "FOUNDED": r'([A-Z][a-z]+\s+[A-Z][a-z]+)\s+founded\s+([\w\s]+)'
        }
        
        triplets = []
        for rel_type, pattern in patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    head = match.group(1).strip()
                    tail = match.group(2).strip()
                    
                    # Clean tail
                    tail = re.sub(r'\s+(?:in|for|by|with|at)\s+\d{4}.*', '', tail)
                    tail = re.sub(r'\s+\$\d+.*', '', tail)
                    
                    if head and tail:
                        triplets.append({
                            "head": head,
                            "relation": rel_type,
                            "tail": tail
                        })
        
        return triplets
    
    def create_graph(self, triplets):
        """Create graph in Neo4j"""
        with self.driver.session() as session:
            # Clear existing data
            session.run("MATCH (n) DETACH DELETE n")
            
            # Create nodes and relationships
            for t in triplets:
                query = """
                MERGE (a:Entity {name: $head})
                MERGE (b:Entity {name: $tail})
                MERGE (a)-[r:RELATION {type: $relation}]->(b)
                """
                session.run(query, head=t["head"], tail=t["tail"], relation=t["relation"])
            
            logger.info(f"✅ Created {len(triplets)} relationships in Neo4j")
    
    def query_graph(self, cypher_query):
        """Execute Cypher query"""
        with self.driver.session() as session:
            result = session.run(cypher_query)
            return [dict(record) for record in result]
    
    def close(self):
        """Close Neo4j connection"""
        self.driver.close()

def main():
    """Main pipeline"""
    logger.info("🚀 Starting Knowledge Graph Pipeline")
    
    # 1. Initialize
    kg = SimpleKG()
    
    try:
        # 2. Read data
        data_path = Path("data/raw_news.txt")
        if not data_path.exists():
            logger.error(f"❌ Data file not found: {data_path}")
            return
        
        with open(data_path, 'r') as f:
            text = f.read()
        
        logger.info(f"📄 Read {len(text)} characters from {data_path}")
        
        # 3. Split into sentences
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        logger.info(f"📝 Split into {len(sentences)} sentences")
        
        # 4. Extract triplets
        all_triplets = []
        for i, sentence in enumerate(sentences, 1):
            triplets = kg.extract_relations(sentence)
            if triplets:
                logger.info(f"  Sentence {i}: '{sentence[:50]}...' -> {len(triplets)} triplets")
                all_triplets.extend(triplets)
        
        logger.info(f"🎯 Total triplets extracted: {len(all_triplets)}")
        
        # 5. Save to CSV
        if all_triplets:
            df = pd.DataFrame(all_triplets)
            output_path = Path("data/triplets.csv")
            df.to_csv(output_path, index=False)
            logger.info(f"💾 Saved triplets to {output_path}")
            
            # 6. Create graph in Neo4j
            kg.create_graph(all_triplets)
            
            # 7. Run sample queries
            queries = [
                "MATCH (n) RETURN n.name as Entity, labels(n) as Labels LIMIT 10",
                "MATCH (a)-[r]->(b) RETURN a.name as From, type(r) as Relationship, b.name as To LIMIT 10",
                "MATCH (n {name: 'Apple'})-[r]->(m) RETURN n.name, type(r), m.name"
            ]
            
            print("\n" + "="*60)
            print("📊 SAMPLE QUERIES RESULTS")
            print("="*60)
            
            for i, query in enumerate(queries, 1):
                print(f"\nQuery {i}: {query}")
                try:
                    results = kg.query_graph(query)
                    if results:
                        for j, row in enumerate(results, 1):
                            print(f"  {j}. {row}")
                    else:
                        print("  No results")
                except Exception as e:
                    print(f"  Error: {e}")
            
            print("\n" + "="*60)
            print("✅ PIPELINE COMPLETED SUCCESSFULLY!")
            print("="*60)
            print("\nNext steps:")
            print("1. Open Neo4j Browser: http://localhost:7474")
            print("2. Login with: neo4j / neo4j")
            print("3. Run queries:")
            print("   • MATCH (n) RETURN n LIMIT 25")
            print("   • MATCH (a)-[r]->(b) RETURN a, r, b")
            print("   • MATCH (n {name: 'Apple'})-[r]->(m) RETURN n, r, m")
        
        else:
            logger.warning("⚠️ No triplets extracted from text")
            
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
    finally:
        kg.close()
        logger.info("🔌 Neo4j connection closed")

if __name__ == "__main__":
    main()
