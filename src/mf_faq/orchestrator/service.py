import logging
from mf_faq.retrieval.service import RetrieverService
from mf_faq.orchestrator.guards import PIIGuard, IntentClassifier, RefusalComposer
from mf_faq.orchestrator.generator import ExtractiveGenerator
from mf_faq.orchestrator.groq_generator import GroqGenerator
from mf_faq.orchestrator.postprocessor import PostProcessor
import os
import dotenv

dotenv.load_dotenv()

logger = logging.getLogger("mf_faq.orchestrator.service")

class OrchestratorService:
    def __init__(self):
        logger.info("Initializing OrchestratorService...")
        self.retriever = RetrieverService()
        self.intent_classifier = IntentClassifier()
        self.refusal_composer = RefusalComposer()
        self.post_processor = PostProcessor()
        # CONFIDENCE_THRESHOLD removed: delegating relevance to Groq
        
        # Initialize Groq if key is present
        self.groq_generator = None
        if os.environ.get("GROQ_API_KEY") and os.environ.get("GROQ_API_KEY") != "your_api_key_here":
            try:
                self.groq_generator = GroqGenerator()
                logger.info("GroqGenerator initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize GroqGenerator: {e}. Falling back to Extractive.")
        
    def ask(self, query: str) -> str:
        """End-to-end Q&A pipeline."""
        
        # 1. PII Guard
        if PIIGuard.check(query):
            logger.warning("PII Guard triggered.")
            draft = "I detected personal information in your request. For your security, I cannot process this query."
            return self.post_processor.process(draft, state='pii')
            
        # 2. Intent Classifier
        intent = self.intent_classifier.classify(query)
        if intent:
            logger.info(f"Refusal Intent triggered: {intent['intent']}")
            # We resolve the scheme to provide a relevant educational link
            scheme_id = self.retriever.resolver.resolve_scheme(query)
            draft = self.refusal_composer.compose(intent, scheme_id)
            return self.post_processor.process(draft, state='refusal')
            
        # 3. Retrieval
        candidates, scheme_id = self.retriever.search(query, top_k=3)
        
        # 4. Empty DB Gate (Only block if we literally found 0 chunks)
        if not candidates:
            logger.info("Empty database. No candidates found.")
            draft = "I don't have a verified answer for that. Please ask about scheme details, exit loads, or AUM."
            return self.post_processor.process(draft, state='dont_know')
            
        # 5. Generator
        best_chunk = candidates[0][0]
        
        if self.groq_generator:
            logger.info("Using Groq LLM for generation.")
            try:
                draft = self.groq_generator.generate(query, best_chunk)
            except Exception as e:
                logger.error(f"Groq generation failed: {e}. Falling back to Extractive.")
                draft = ExtractiveGenerator.generate(best_chunk)
        else:
            logger.info("Using Extractive generation.")
            draft = ExtractiveGenerator.generate(best_chunk)
            
        # 5.5 Check if Groq gracefully rejected the fact
        if "I don't have a verified answer" in draft:
            return self.post_processor.process(draft, state='dont_know')
        
        # 6. Post-Processor
        final_answer = self.post_processor.process(
            draft, 
            state='factual', 
            source_url=best_chunk.source_url, 
            last_updated=best_chunk.last_updated
        )
        
        return final_answer
