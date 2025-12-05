import logging
from typing import Optional, Dict, List
import re
from .prompts import NL_TO_CYPHER_PROMPT
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


class NaturalLanguageQuery:
    def __init__(self, config: Dict):
        self.config = config
        neo4j_config = config['neo4j']

        self.driver = GraphDatabase.driver(
            neo4j_config['uri'],
            auth=(neo4j_config['username'], neo4j_config['password'])
        )

        # Predefined query templates
        self.query_templates = {
            'company acquisitions': """
                MATCH (c:Company)-[r:ACQUIRED]->(target)
                RETURN c.name as acquirer, target.name as acquired_company, 
                       r.confidence as confidence
                ORDER BY r.confidence DESC
                LIMIT 10
            """,
            'company investments': """
                MATCH (c:Company)-[r:INVESTED_IN]->(target)
                RETURN c.name as investor, target.name as investment, 
                       r.confidence as confidence
                ORDER BY r.confidence DESC
                LIMIT 10
            """,
            'person companies': """
                MATCH (p:Person)-[r:CEO_OF]->(c:Company)
                RETURN p.name as person, c.name as company, 
                       r.confidence as confidence
                ORDER BY r.confidence DESC
                LIMIT 10
            """,
            'product launches': """
                MATCH (c:Company)-[r:LAUNCHED]->(p:Product)
                RETURN c.name as company, p.name as product, 
                       r.confidence as confidence
                ORDER BY r.confidence DESC
                LIMIT 10
            """
        }

    def query_to_cypher(self, question: str, use_llm: bool = False) -> Optional[str]:
        """Convert natural language question to Cypher query"""
        question_lower = question.lower().strip()

        # Check for predefined patterns
        for pattern, template in self.query_templates.items():
            if pattern in question_lower:
                logger.info(f"Using predefined template for: {pattern}")
                return template

        # Use LLM for complex queries if enabled
        if use_llm and self.config['llm']['mode'] == 'api':
            return self._llm_to_cypher(question)

        # Simple rule-based conversion
        return self._rule_based_conversion(question)

    def _llm_to_cypher(self, question: str) -> Optional[str]:
        """Use LLM to convert question to Cypher"""
        try:
            import openai

            prompt = NL_TO_CYPHER_PROMPT.format(question=question)

            response = openai.ChatCompletion.create(
                model=self.config['llm']['api_model'],
                messages=[
                    {"role": "system", "content": "You are a Cypher query generator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )

            cypher = response.choices[0].message.content.strip()

            # Clean up response
            cypher = cypher.replace('```cypher', '').replace('```', '').strip()

            logger.info(f"LLM generated Cypher: {cypher}")
            return cypher

        except Exception as e:
            logger.error(f"LLM query conversion failed: {e}")
            return None

    def _rule_based_conversion(self, question: str) -> Optional[str]:
        """Simple rule-based conversion to Cypher"""
        question_lower = question.lower()

        # Pattern matching rules
        patterns = [
            (r'what companies did (.+?) acquire',
             "MATCH (c:Company {name: $company})-[:ACQUIRED]->(target) RETURN target.name"),
            (r'who invested in (.+?)',
             "MATCH (investor)-[:INVESTED_IN]->(c:Company {name: $company}) RETURN investor.name"),
            (r'what products did (.+?) launch',
             "MATCH (c:Company {name: $company})-[:LAUNCHED]->(p:Product) RETURN p.name"),
            (r'who is the ceo of (.+?)',
             "MATCH (p:Person)-[:CEO_OF]->(c:Company {name: $company}) RETURN p.name"),
            (r'what companies partnered with (.+?)',
             "MATCH (c:Company)-[:PARTNERED_WITH]->(target:Company {name: $company}) RETURN c.name"),
        ]

        for pattern, template in patterns:
            match = re.search(pattern, question_lower)
            if match:
                entity = match.group(1).strip()
                return template.replace('$company', f"'{entity.title()}'")

        # Default query
        return """
            MATCH (n)-[r]->(m)
            WHERE n.name CONTAINS $term OR m.name CONTAINS $term
            RETURN n.name as source, type(r) as relationship, m.name as target
            LIMIT 10
        """

    def execute_query(self, cypher_query: str, params: Dict = None) -> List[Dict]:
        """Execute Cypher query and return results"""
        if params is None:
            params = {}

        try:
            with self.driver.session() as session:
                result = session.run(cypher_query, params)

                # Convert to list of dictionaries
                records = []
                for record in result:
                    records.append(dict(record))

                logger.info(f"Query executed, returned {len(records)} records")
                return records

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return []

    def ask_question(self, question: str) -> List[Dict]:
        """Complete pipeline: question -> Cypher -> results"""
        logger.info(f"Processing question: {question}")

        # Convert to Cypher
        cypher = self.query_to_cypher(question)

        if not cypher:
            logger.warning("Could not convert question to Cypher")
            return []

        logger.info(f"Generated Cypher: {cypher}")

        # Execute query
        results = self.execute_query(cypher)

        return results

    def close(self):
        """Close Neo4j driver"""
        self.driver.close()


if __name__ == "__main__":
    # Test NL query
    config = {
        'neo4j': {
            'uri': 'bolt://localhost:7687',
            'username': 'neo4j',
            'password': 'password'
        },
        'llm': {
            'mode': 'local'
        }
    }

    nlq = NaturalLanguageQuery(config)

    test_questions = [
        "What companies did Apple acquire?",
        "Who invested in OpenAI?",
        "What products did Tesla launch?"
    ]

    for question in test_questions:
        print(f"\nQuestion: {question}")
        cypher = nlq.query_to_cypher(question)
        print(f"Cypher: {cypher}")

    nlq.close()