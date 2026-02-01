# intent_detector.py
# Domain-aware query intent detection for routing to appropriate retrievers
from typing import Dict, List, Tuple
import re

class DomainIntentDetector:
    """
    Detects query intent and domain (disease, climate, soil, policy) 
    without requiring LLM calls - using keyword matching and heuristics.
    """
    
    # Domain-specific keywords for deterministic detection
    DOMAIN_KEYWORDS = {
        "disease": {
            "keywords": [
                "disease", "symptom", "infection", "pathogen", "fungal", "bacterial", 
                "viral", "pest", "insect", "infestation", "lesion", "blight", "rust", 
                "mildew", "scab", "wilt", "rot", "canker", "damping-off", "yellowing",
                "spotting", "blotch", "stripe", "necrosis", "prevention", "treatment",
                "management", "control", "resistant", "susceptible", "tolerance"
            ],
            "patterns": [
                r"(yellow|stripe|stem|leaf|powdery|septoria)\s+rust",
                r"(fusarium|head|blight)",
                r"(powdery)\s+(mildew)",
                r"(take[- ]?all)",
                r"(wheat\s+blast)",
                r"(bacterial\s+leaf\s+streak)",
                r"(tan\s+spot)",
            ],
            "aliases": ["disease", "disorder", "pathology", "infection"]
        },
        "climate": {
            "keywords": [
                "climate", "weather", "temperature", "rainfall", "precipitation", 
                "humidity", "moisture", "drought", "flood", "rain", "snow", "frost",
                "heat", "cold", "wind", "season", "monsoon", "irrigation", "water",
                "drought stress", "heat stress", "cold stress", "wet", "dry",
            ],
            "patterns": [
                r"(rainfall|precipitation|rain|moisture)\s+(pattern|forecast|requirement)",
                r"(temperature|heat|frost|cold)\s+(stress|requirement|tolerance)",
                r"(drought|flood|irrigation|water)",
                r"(climate|weather|monsoon|season)",
            ],
            "aliases": ["weather", "environmental", "precipitation", "moisture"]
        },
        "soil": {
            "keywords": [
                "soil", "earth", "ground", "fertility", "nutrient", "nitrogen", "phosphorus",
                "potassium", "pH", "acidity", "alkalinity", "organic", "humus", "texture",
                "structure", "drainage", "compaction", "salinity", "iron", "zinc", "boron",
                "deficiency", "amendment", "compost", "manure", "fertilizer", "NPK", "water"
            ],
            "patterns": [
                r"(soil|ground|earth)\s+(fertility|health|quality|condition|texture|structure|pH)",
                r"(nitrogen|phosphorus|potassium|NPK|nutrient)\s+(deficiency|requirement)",
                r"(soil\s+water|drainage|moisture|waterlogging)",
                r"(organic\s+matter|humus|fertility)",
            ],
            "aliases": ["ground", "earth", "fertility", "nutrients"]
        },
        "policy": {
            "keywords": [
                "policy", "regulation", "subsidy", "grant", "loan", "insurance", 
                "certification", "standard", "guideline", "law", "rule", "requirement",
                "government", "ministry", "scheme", "program", "support", "assistance",
                "minimum support price", "MSP", "procurement", "export", "import"
            ],
            "patterns": [
                r"(government|policy|subsidy|grant|loan)",
                r"(certification|standard|quality|export|import)",
                r"(minimum\s+support\s+price|MSP|procurement)",
                r"(scheme|program|assistance|support)",
            ],
            "aliases": ["regulation", "government", "scheme", "certification"]
        }
    }
    
    @staticmethod
    def detect_domain(query: str) -> Dict:
        """
        Detect query domain and intent using keyword matching.
        
        Args:
            query: User query string
            
        Returns:
            Dict with:
                - domain: Primary domain (disease|climate|soil|policy)
                - confidence: Confidence score 0-1
                - secondary_domains: List of other detected domains
                - intent_keywords: Keywords that triggered the detection
                - route_to: List of retrievers to use
        """
        query_lower = query.lower()
        domain_scores = {}
        matched_keywords = {}
        
        # Score each domain
        for domain, config in DomainIntentDetector.DOMAIN_KEYWORDS.items():
            score = 0
            matched = []
            
            # Check keyword matches
            for keyword in config["keywords"]:
                if keyword.lower() in query_lower:
                    score += 1
                    matched.append(keyword)
            
            # Check pattern matches (higher weight)
            for pattern in config["patterns"]:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    score += 3
                    matched.append(f"pattern:{pattern[:20]}")
            
            domain_scores[domain] = score
            matched_keywords[domain] = matched
        
        # Normalize scores
        max_score = max(domain_scores.values()) if domain_scores else 0
        
        if max_score == 0:
            # No clear domain - route to all (fallback)
            return {
                "domain": "general",
                "confidence": 0.0,
                "secondary_domains": [],
                "intent_keywords": [],
                "route_to": ["disease", "climate", "soil", "policy"]
            }
        
        # Get primary domain
        primary_domain = max(domain_scores, key=domain_scores.get)
        confidence = min(1.0, domain_scores[primary_domain] / max_score)
        
        # Get secondary domains (score > 0.5 of primary)
        secondary_domains = [
            d for d, score in domain_scores.items()
            if d != primary_domain and score > max_score * 0.3
        ]
        
        # Determine which retrievers to route to
        if confidence > 0.7:
            # High confidence - use only primary
            route_to = [primary_domain]
        elif confidence > 0.5:
            # Medium confidence - use primary + secondary
            route_to = [primary_domain] + secondary_domains
        else:
            # Low confidence - check all
            route_to = [primary_domain] + secondary_domains
            if len(route_to) < 2:
                route_to = ["disease", "climate", "soil", "policy"]
        
        return {
            "domain": primary_domain,
            "confidence": confidence,
            "secondary_domains": secondary_domains,
            "intent_keywords": matched_keywords.get(primary_domain, [])[:5],  # Top 5
            "route_to": list(set(route_to))  # Remove duplicates
        }
    
    @staticmethod
    def extract_query_keywords(query: str, top_n: int = 5) -> List[str]:
        """
        Extract important keywords from query for keyword overlap scoring.
        Removes stop words and returns only meaningful terms.
        
        Args:
            query: User query
            top_n: Number of keywords to extract
            
        Returns:
            List of important keywords
        """
        # Common stop words to exclude
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'am', 'been', 'be', 'have', 'has',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'can', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which',
            'where', 'when', 'why', 'how', 'this', 'that', 'these', 'those',
            'what', 'is', 'how', 'if', 'then'
        }
        
        # Split and clean
        words = re.findall(r'\b[a-z]+\b', query.lower())
        
        # Filter stop words and get unique, meaningful terms
        keywords = []
        seen = set()
        for word in words:
            if word not in stop_words and word not in seen and len(word) > 2:
                keywords.append(word)
                seen.add(word)
                if len(keywords) >= top_n:
                    break
        
        return keywords if keywords else [w for w in words if len(w) > 2][:top_n]


# Example usage
if __name__ == "__main__":
    test_queries = [
        "What are the symptoms of yellow rust in wheat?",
        "How much rainfall does wheat need during monsoon season?",
        "What is the soil pH required for wheat cultivation?",
        "Is wheat eligible for government subsidy under the PM scheme?",
        "How do I prevent both disease and manage water in wheat?",
    ]
    
    detector = DomainIntentDetector()
    
    for query in test_queries:
        result = detector.detect_domain(query)
        keywords = detector.extract_query_keywords(query)
        print(f"\nQuery: {query}")
        print(f"Domain: {result['domain']} (confidence: {result['confidence']:.2f})")
        print(f"Route to: {result['route_to']}")
        print(f"Keywords: {keywords}")
