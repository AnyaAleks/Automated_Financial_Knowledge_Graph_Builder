import json
import logging
from typing import List, Dict, Any
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from .prompts import EXTRACTION_PROMPT_ZERO_SHOT, EXTRACTION_PROMPT_FEW_SHOT
import re

logger = logging.getLogger(__name__)


class EntityRelationshipExtractor:
    def __init__(self, config: Dict):
        self.config = config
        self.mode = config['llm']['mode']
        self.entity_types = config['extraction']['entity_types']
        self.relation_types = config['extraction']['relation_types']

        if self.mode == "local":
            self._setup_local_model()
        elif self.mode == "api":
            self._setup_api_model()
        else:
            raise ValueError(f"Unknown LLM mode: {self.mode}")

    def _setup_local_model(self):
        """Setup local LLM model"""
        model_name = self.config['llm']['local_model']
        device = self.config['llm']['device']

        logger.info(f"Loading local model: {model_name} on {device}")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                low_cpu_mem_usage=True
            )

            if device == "cpu":
                self.model = self.model.to("cpu")

            logger.info("Local model loaded successfully")

        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            raise

    def _setup_api_model(self):
        """Setup API-based model (OpenAI)"""
        # For OpenAI API
        import openai
        openai.api_key = self.config['llm']['api_key']
        self.api_client = openai
        logger.info("API model configured")

    def extract_from_text(self, text: str, use_few_shot: bool = False) -> List[Dict]:
        """Extract entities and relationships from text"""
        if self.mode == "local":
            return self._extract_local(text, use_few_shot)
        else:
            return self._extract_api(text, use_few_shot)

    def _extract_local(self, text: str, use_few_shot: bool) -> List[Dict]:
        """Extract using local model"""
        if use_few_shot:
            prompt = EXTRACTION_PROMPT_FEW_SHOT.format(text=text)
        else:
            prompt = EXTRACTION_PROMPT_ZERO_SHOT.format(
                entity_types=", ".join(self.entity_types),
                relation_types=", ".join(self.relation_types),
                text=text
            )

        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048)

        if self.config['llm']['device'] == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=500,
                temperature=0.1,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Parse JSON from response
        triplets = self._parse_response(response)

        return triplets

    def _extract_api(self, text: str, use_few_shot: bool) -> List[Dict]:
        """Extract using API (OpenAI)"""
        if use_few_shot:
            messages = [
                {"role": "system", "content": "You are a financial knowledge graph extraction assistant."},
                {"role": "user", "content": EXTRACTION_PROMPT_FEW_SHOT.format(text=text)}
            ]
        else:
            messages = [
                {"role": "system", "content": "You are a financial knowledge graph extraction assistant."},
                {"role": "user", "content": EXTRACTION_PROMPT_ZERO_SHOT.format(
                    entity_types=", ".join(self.entity_types),
                    relation_types=", ".join(self.relation_types),
                    text=text
                )}
            ]

        try:
            response = self.api_client.ChatCompletion.create(
                model=self.config['llm']['api_model'],
                messages=messages,
                temperature=0.1,
                max_tokens=500
            )

            content = response.choices[0].message.content
            triplets = self._parse_response(content)
            return triplets

        except Exception as e:
            logger.error(f"API extraction error: {e}")
            return []

    def _parse_response(self, response: str) -> List[Dict]:
        """Parse JSON response from LLM"""
        # Find JSON array in response
        json_match = re.search(r'\[.*\]', response, re.DOTALL)

        if not json_match:
            logger.warning("No JSON array found in response")
            return []

        json_str = json_match.group()

        try:
            triplets = json.loads(json_str)

            # Validate triplet structure
            validated = []
            for triplet in triplets:
                if all(key in triplet for key in ['head', 'relation', 'tail']):
                    # Add confidence if missing
                    if 'confidence' not in triplet:
                        triplet['confidence'] = 0.8

                    # Ensure confidence is float
                    triplet['confidence'] = float(triplet['confidence'])

                    validated.append(triplet)

            logger.info(f"Extracted {len(validated)} valid triplets")
            return validated

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return []


if __name__ == "__main__":
    # Test extraction
    config = {
        'llm': {
            'mode': 'local',
            'local_model': 'Qwen/Qwen2.5-7B-Instruct',
            'device': 'cpu'
        },
        'extraction': {
            'entity_types': ['COMPANY', 'PERSON', 'PRODUCT'],
            'relation_types': ['ACQUIRED', 'LAUNCHED', 'CEO_OF']
        }
    }

    extractor = EntityRelationshipExtractor(config)
    test_text = "Apple acquired AI startup DarwinAI in 2024."
    triplets = extractor.extract_from_text(test_text)
    print(f"Extracted triplets: {json.dumps(triplets, indent=2)}")