"""
Prompt templates for LLM-based entity and relationship extraction
"""

EXTRACTION_PROMPT_ZERO_SHOT = """
You are a financial knowledge graph extraction assistant. Extract all entities and relationships from the given text.

ENTITY TYPES:
{entity_types}

RELATIONSHIP TYPES:
{relation_types}

INSTRUCTIONS:
1. Identify all entities mentioned in the text
2. Identify all relationships between entities
3. Format output as JSON list of triplets
4. Each triplet: {{"head": entity1, "relation": relationship, "tail": entity2, "confidence": 0.0-1.0}}

EXAMPLE OUTPUT:
[
  {{"head": "Apple", "relation": "ACQUIRED", "tail": "DarwinAI", "confidence": 0.95}},
  {{"head": "Tesla", "relation": "LAUNCHED", "tail": "Model Y", "confidence": 0.88}}
]

TEXT TO EXTRACT FROM:
{text}

EXTRACTION:
"""

EXTRACTION_PROMPT_FEW_SHOT = """
Extract financial entities and relationships from text.

Examples:
Text: "Apple acquired AI startup DarwinAI for $100 million in January 2024."
Output: [
  {{"head": "Apple", "relation": "ACQUIRED", "tail": "DarwinAI", "confidence": 0.95}},
  {{"head": "DarwinAI", "relation": "ACQUISITION_PRICE", "tail": "$100 million", "confidence": 0.85}},
  {{"head": "Apple", "relation": "ACQUISITION_DATE", "tail": "January 2024", "confidence": 0.90}}
]

Text: "Tesla's CEO Elon Musk announced the launch of Model Y electric SUV."
Output: [
  {{"head": "Elon Musk", "relation": "CEO_OF", "tail": "Tesla", "confidence": 0.98}},
  {{"head": "Tesla", "relation": "LAUNCHED", "tail": "Model Y", "confidence": 0.92}},
  {{"head": "Model Y", "relation": "PRODUCT_TYPE", "tail": "electric SUV", "confidence": 0.88}}
]

Now extract from this text:
{text}
"""

VALIDATION_PROMPT = """
Validate the following extracted triplet for correctness:

Text: {text}
Triplet: {triplet}

Instructions:
1. Check if the entities exist in the text
2. Check if the relationship is correctly identified
3. Check if the relationship direction is correct
4. Return JSON: {{"is_valid": true/false, "confidence": 0.0-1.0, "issues": ["list of issues"]}}
"""

NL_TO_CYPHER_PROMPT = """
Convert the natural language question to a Cypher query for Neo4j knowledge graph.

Knowledge Graph Schema:
- Node labels: Entity, Company, Person, Product, Event
- Node properties: name, type, description
- Relationship types: ACQUIRED, INVESTED_IN, LAUNCHED, PARTNERED_WITH, CEO_OF, FOUNDED

Question: {question}

Cypher Query (return only the query, no explanation):
"""