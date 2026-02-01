# domain_retrievers.py
# Specialized retrievers for each agricultural domain
from typing import List, Tuple
from RAG.vectorstore import similarity_search
import re

class DomainRetriever:
    """Base retriever with common functionality"""
    
    def __init__(self, domain: str, data_type: str, crop: str = "Wheat"):
        self.domain = domain
        self.data_type = data_type
        self.crop = crop
    
    def retrieve(self, query: str, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Retrieve documents for the domain.
        
        Returns:
            List of (content, similarity_score) tuples
        """
        try:
            results = similarity_search(
                query=query,
                data_type=self.data_type,
                crop=self.crop,
                province="Punjab",
                limit=limit
            )
            return results
        except Exception as e:
            print(f"⚠️  Error in {self.domain} retriever: {str(e)}")
            return []
    
    def calculate_keyword_overlap(self, content: str, keywords: List[str]) -> int:
        """
        Calculate keyword overlap score between content and query keywords.
        
        Args:
            content: Document content
            keywords: Query keywords to match
            
        Returns:
            Number of keywords found in content
        """
        content_lower = content.lower()
        score = 0
        for keyword in keywords:
            if keyword.lower() in content_lower:
                score += 1
        return score


class DiseaseRetriever(DomainRetriever):
    """Retriever for disease-related queries"""
    
    DISEASE_KEYWORDS = {
        "yellow rust": ["yellow rust", "stripe rust", "puccinia striiformis", "puccinia graminis"],
        "powdery mildew": ["powdery mildew", "blumeria graminis"],
        "septoria": ["septoria", "septoria leaf blotch", "mycosphaerella graminicola"],
        "fusarium": ["fusarium", "fusarium head blight", "scab", "fusarium graminearum"],
        "tan spot": ["tan spot", "pyrenophora tritici-repentis"],
        "leaf rust": ["leaf rust", "puccinia triticina"],
        "stem rust": ["stem rust", "black rust", "puccinia graminis"],
        "wheat blast": ["wheat blast", "magnaporthe oryzae"],
        "bacterial": ["bacterial leaf streak", "xanthomonas translucens"],
        "take-all": ["take-all", "gaumannomyces graminis"]
    }
    
    def __init__(self):
        super().__init__(domain="disease", data_type="disease", crop="Wheat")
    
    def calculate_keyword_overlap(self, content: str, keywords: List[str]) -> int:
        """Enhanced scoring for disease-related terms"""
        score = super().calculate_keyword_overlap(content, keywords)
        
        # Bonus for disease-specific patterns
        patterns = [
            r'(yellow\s+rust|stripe\s+rust|puccinia)',
            r'(powdery\s+mildew|blumeria)',
            r'(septoria|leaf\s+blotch)',
            r'(fusarium|head\s+blight|scab)',
            r'(tan\s+spot|pyrenophora)',
            r'(leaf\s+rust|stem\s+rust|black\s+rust)',
            r'(wheat\s+blast|magnaporthe)',
            r'(bacterial\s+leaf\s+streak|xanthomonas)',
            r'(take-all|gaumannomyces)',
            r'(symptom|infection|resistance|susceptib)',
        ]
        
        content_lower = content.lower()
        for pattern in patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                score += 2
        
        return score


class ClimateRetriever(DomainRetriever):
    """Retriever for climate and weather-related queries"""
    
    CLIMATE_KEYWORDS = [
        "rainfall", "precipitation", "temperature", "humidity", "drought",
        "flood", "monsoon", "irrigation", "water requirement", "weather pattern",
        "seasonal", "frost", "heat stress", "cold stress", "moisture"
    ]
    
    def __init__(self):
        super().__init__(domain="climate", data_type="climate", crop="Wheat")
    
    def calculate_keyword_overlap(self, content: str, keywords: List[str]) -> int:
        """Enhanced scoring for climate-related terms"""
        score = super().calculate_keyword_overlap(content, keywords)
        
        # Bonus for climate-specific patterns
        patterns = [
            r'(\d+\s*(?:mm|cm|inches)\s+(?:rainfall|precipitation))',
            r'(\d+[°c|°f]\s+(?:temperature|temp))',
            r'(\d+\s*(?:%|percent)\s+(?:humidity|moisture))',
        ]
        
        content_lower = content.lower()
        for pattern in patterns:
            if re.search(pattern, content_lower):
                score += 2
        
        return score


class SoilRetriever(DomainRetriever):
    """Retriever for soil and fertility-related queries"""
    
    SOIL_KEYWORDS = [
        "soil", "fertility", "nutrient", "nitrogen", "phosphorus", "potassium",
        "pH", "organic matter", "drainage", "texture", "deficiency", "amendment",
        "NPK", "trace elements", "zinc", "iron", "boron", "compaction"
    ]
    
    def __init__(self):
        super().__init__(domain="soil", data_type="soil", crop="Wheat")
    
    def calculate_keyword_overlap(self, content: str, keywords: List[str]) -> int:
        """Enhanced scoring for soil-related metrics"""
        score = super().calculate_keyword_overlap(content, keywords)
        
        # Bonus for soil metrics
        patterns = [
            r'(ph\s*[=:]?\s*[\d.]+)',
            r'(nitrogen|phosphorus|potassium|npk)',
            r'([\d.]+\s*(?:kg|ton|g)\s+(?:per|/)\s+hectare)',
        ]
        
        content_lower = content.lower()
        for pattern in patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                score += 2
        
        return score


class PolicyRetriever(DomainRetriever):
    """Retriever for policy and scheme-related queries"""
    
    POLICY_KEYWORDS = [
        "policy", "scheme", "subsidy", "grant", "loan", "certification",
        "regulation", "standard", "MSP", "minimum support price", "procurement",
        "insurance", "government", "eligible", "requirement", "guideline"
    ]
    
    def __init__(self):
        super().__init__(domain="policy", data_type="policy", crop="Wheat")
    
    def calculate_keyword_overlap(self, content: str, keywords: List[str]) -> int:
        """Enhanced scoring for policy-related terms"""
        score = super().calculate_keyword_overlap(content, keywords)
        
        # Bonus for policy-specific keywords
        patterns = [
            r'(eligibility|eligible|requirement)',
            r'(rupees|rs|₹)\s*[\d,]+',
            r'(scheme|program|policy|guideline)',
        ]
        
        content_lower = content.lower()
        for pattern in patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                score += 2
        
        return score


# Orchestrator for all retrievers
class RetrieverOrchestrator:
    """Manages all domain-specific retrievers"""
    
    def __init__(self):
        self.retrievers = {
            "disease": DiseaseRetriever(),
            "climate": ClimateRetriever(),
            "soil": SoilRetriever(),
            "policy": PolicyRetriever(),
        }
    
    def retrieve_from_domains(self, domains: List[str], query: str, 
                             keywords: List[str], limit: int = 10) -> List[Tuple[str, float, str]]:
        """
        Retrieve from specified domains and re-rank by similarity + keyword overlap.
        
        Args:
            domains: List of domain names to retrieve from
            query: User query
            keywords: Extracted keywords from query
            limit: Number of results per domain
            
        Returns:
            List of (content, combined_score, domain) tuples, sorted by score
        """
        all_results = []
        
        for domain in domains:
            if domain not in self.retrievers:
                continue
            
            retriever = self.retrievers[domain]
            results = retriever.retrieve(query, limit=limit)
            
            # Score each result
            for content, vector_score in results:
                keyword_overlap = retriever.calculate_keyword_overlap(content, keywords)
                
                # Combined score: balance vector similarity with keyword overlap
                # vector_score is distance (lower is better)
                # keyword_overlap is count (higher is better)
                if keyword_overlap > 0:
                    combined_score = vector_score / (keyword_overlap + 1)
                else:
                    combined_score = vector_score * 2  # Penalize if no keywords
                
                all_results.append((content, combined_score, domain))
        
        # Sort by combined_score (lower is better)
        all_results.sort(key=lambda x: x[1])
        
        return all_results

if __name__ == "__main__":
    # Test retrievers
    orchestrator = RetrieverOrchestrator()
    
    test_cases = [
        ("disease", ["yellow", "rust", "symptoms"], ["disease"]),
        ("climate", ["rainfall", "requirement"], ["climate"]),
        ("soil", ["pH", "nutrient"], ["soil"]),
        ("policy", ["subsidy", "scheme"], ["policy"]),
    ]
    
    for domain, keywords, domains_to_query in test_cases:
        print(f"\n🧪 Testing {domain} retriever with keywords: {keywords}")
        results = orchestrator.retrieve_from_domains(
            domains=domains_to_query,
            query=" ".join(keywords),
            keywords=keywords,
            limit=5
        )
        print(f"Retrieved {len(results)} results from {domain}")
        for content, score, d in results[:2]:
            print(f"  - Score: {score:.4f}, Content: {content[:80]}...")
