import pandas as pd
import logging
from typing import List, Dict, Tuple
import re

logger = logging.getLogger(__name__)


class DataCleaner:
    def __init__(self, config: Dict):
        self.config = config
        self.confidence_threshold = config['pipeline']['confidence_threshold']

        # Standardization mappings
        self.relation_standardization = {
            'acquired': 'ACQUIRED',
            'acquisition': 'ACQUIRED',
            'bought': 'ACQUIRED',
            'purchased': 'ACQUIRED',
            'invested in': 'INVESTED_IN',
            'investment in': 'INVESTED_IN',
            'funded': 'INVESTED_IN',
            'launched': 'LAUNCHED',
            'released': 'LAUNCHED',
            'introduced': 'LAUNCHED',
            'partnered with': 'PARTNERED_WITH',
            'collaborated with': 'PARTNERED_WITH',
            'ceo of': 'CEO_OF',
            'chief executive officer of': 'CEO_OF',
            'founded': 'FOUNDED',
            'established': 'FOUNDED',
            'created': 'FOUNDED'
        }

    def clean_triplets(self, triplets: List[Dict]) -> pd.DataFrame:
        """Clean and standardize extracted triplets"""
        if not triplets:
            return pd.DataFrame()

        # Convert to DataFrame
        df = pd.DataFrame(triplets)

        if df.empty:
            return df

        # 1. Remove duplicates
        initial_count = len(df)
        df.drop_duplicates(subset=['head', 'relation', 'tail'], inplace=True)
        logger.info(f"Removed {initial_count - len(df)} duplicate triplets")

        # 2. Filter by confidence
        if 'confidence' in df.columns:
            df = df[df['confidence'] >= self.confidence_threshold].copy()
            logger.info(f"Filtered to {len(df)} triplets above confidence {self.confidence_threshold}")

        # 3. Standardize relations
        df['relation'] = df['relation'].apply(self._standardize_relation)

        # 4. Clean entity names
        df['head'] = df['head'].apply(self._clean_entity_name)
        df['tail'] = df['tail'].apply(self._clean_entity_name)

        # 5. Remove invalid relations
        valid_relations = self.config['extraction']['relation_types']
        df = df[df['relation'].isin(valid_relations)].copy()

        # 6. Remove self-references
        df = df[df['head'] != df['tail']].copy()

        # 7. Add entity types if missing
        if 'head_type' not in df.columns:
            df['head_type'] = df['head'].apply(self._infer_entity_type)
        if 'tail_type' not in df.columns:
            df['tail_type'] = df['tail'].apply(self._infer_entity_type)

        # 8. Sort by confidence (if available)
        if 'confidence' in df.columns:
            df = df.sort_values('confidence', ascending=False)

        logger.info(f"Cleaned data: {len(df)} valid triplets")
        return df

    def _standardize_relation(self, relation: str) -> str:
        """Standardize relation names"""
        if pd.isna(relation):
            return "UNKNOWN"

        relation_str = str(relation).strip().lower()

        # Check direct mapping
        if relation_str in self.relation_standardization:
            return self.relation_standardization[relation_str]

        # Check if any key is contained in the relation
        for key, value in self.relation_standardization.items():
            if key in relation_str:
                return value

        # Return uppercase version
        return relation_str.upper()

    def _clean_entity_name(self, entity: str) -> str:
        """Clean entity name"""
        if pd.isna(entity):
            return ""

        entity_str = str(entity).strip()

        # Remove extra whitespace
        entity_str = re.sub(r'\s+', ' ', entity_str)

        # Remove trailing/leading quotes
        entity_str = entity_str.strip('"\'')

        # Capitalize first letter of each word for proper nouns
        if entity_str.isupper() or entity_str.islower():
            entity_str = entity_str.title()

        return entity_str

    def _infer_entity_type(self, entity: str) -> str:
        """Infer entity type from name patterns"""
        if pd.isna(entity):
            return "UNKNOWN"

        entity_str = str(entity)

        # Company patterns
        company_patterns = ['Inc', 'Corp', 'Ltd', 'LLC', 'Co.', 'Company', 'Group']
        if any(pattern in entity_str for pattern in company_patterns):
            return "COMPANY"

        # Person patterns (capitalized names)
        if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', entity_str):
            return "PERSON"

        # Date patterns
        date_patterns = [r'\d{4}', r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b']
        for pattern in date_patterns:
            if re.search(pattern, entity_str):
                return "DATE"

        # Currency patterns
        currency_patterns = [r'\$\d+', r'\d+\s*(million|billion|trillion)', r'USD', r'EUR']
        for pattern in currency_patterns:
            if re.search(pattern, entity_str, re.IGNORECASE):
                return "CURRENCY"

        return "ENTITY"


if __name__ == "__main__":
    # Test cleaning
    config = {
        'pipeline': {'confidence_threshold': 0.7},
        'extraction': {
            'relation_types': ['ACQUIRED', 'INVESTED_IN', 'LAUNCHED', 'PARTNERED_WITH']
        }
    }

    cleaner = DataCleaner(config)

    test_triplets = [
        {"head": "Apple", "relation": "acquired", "tail": "DarwinAI", "confidence": 0.95},
        {"head": "Apple", "relation": "bought", "tail": "DarwinAI", "confidence": 0.85},
        {"head": "apple", "relation": "ACQUIRED", "tail": "darwinai", "confidence": 0.6},
    ]

    df = cleaner.clean_triplets(test_triplets)
    print("Cleaned DataFrame:")
    print(df)