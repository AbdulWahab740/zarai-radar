# orchestrator_agent.py
# Agentic ReAct flow with reasoning, adaptive tool use, and Supabase-backed conversation history
# Agent reasons about queries, decides which tools to call, and maintains conversation memory with chat titles

from typing import Dict, List, Tuple, Any, Optional
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import json
from datetime import datetime
import time

from RAG.intent_detector import DomainIntentDetector
from RAG.domain_retrievers import RetrieverOrchestrator
from RAG.llm_loader import load_llm
from RAG.conversation_history import ConversationHistoryManager
llm = load_llm()

# ============================================================================
# AGENT TOOLS (Tool-calling interface)
# ============================================================================

# Global tool state
_intent_detector = DomainIntentDetector()
_retriever_orchestrator = RetrieverOrchestrator()
_previous_intents = {}
_retrieved_context = {}

@tool
def analyze_query_intent(query: str) -> str:
    """
    Analyze query intent and domain for routing.
    Determines primary domain and routing strategy.
    
    Args:
        query: The user's question
        
    Returns:
        JSON string with domain, confidence, and routing strategy
    """
    try:
        intent = _intent_detector.detect_domain(query)
        keywords = _intent_detector.extract_query_keywords(query, top_n=5)
        
        result = {
            "domain": intent["domain"],
            "confidence": round(intent["confidence"], 2),
            "route_to": intent["route_to"],
            "keywords": keywords,
            "intent_keywords": intent["intent_keywords"]
        }
        _previous_intents[query] = result
        return json.dumps(result)
    except Exception as e:
        return json.dumps({
            "error": str(e),
            "route_to": ["disease", "climate", "soil", "policy"]
        })

@tool
def retrieve_documents_from_domain(domain: str, query: str, 
                                   keywords: str = "", limit: int = 10) -> str:
    """
    Retrieve documents from a specific domain.
    Use this to search in particular domains (disease, climate, soil, policy).
    
    Args:
        domain: Target domain (disease, climate, soil, or policy)
        query: Search query
        keywords: Comma-separated keywords for scoring (optional)
        limit: Maximum documents to retrieve
        
    Returns:
        JSON string with top documents and relevance scores
    """
    try:
        keyword_list = [k.strip() for k in keywords.split(",")] if keywords else []
        
        results = _retriever_orchestrator.retrieve_from_domains(
            domains=[domain],
            query=query,
            keywords=keyword_list,
            limit=limit
        )
        
        formatted = [
            {
                "content": content[:400],
                "score": round(score, 4),
                "domain": domain
            }
            for content, score, dom in results[:5]  # Top 5 per domain
        ]
        
        result = {
            "domain": domain,
            "total_found": len(results),
            "returned": len(formatted),
            "documents": formatted
        }
        _retrieved_context[domain] = formatted
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "documents": []})

@tool
def retrieve_multi_domain_documents(domains: str, query: str, 
                                   keywords: str = "", limit: int = 10) -> str:
    """
    Retrieve documents from multiple domains simultaneously.
    Use when answer needs information from multiple areas.
    
    Args:
        domains: Comma-separated domain list (disease,climate,soil,policy)
        query: Search query
        keywords: Comma-separated keywords for scoring
        limit: Total results to return (distributed across domains)
        
    Returns:
        JSON string with merged top documents from all domains
    """
    try:
        domain_list = [d.strip() for d in domains.split(",")]
        keyword_list = [k.strip() for k in keywords.split(",")] if keywords else []
        
        results = _retriever_orchestrator.retrieve_from_domains(
            domains=domain_list,
            query=query,
            keywords=keyword_list,
            limit=limit
        )
        
        top_results = results[:7]
        formatted = [
            {
                "content": content[:400],
                "score": round(score, 4),
                "domain": domain
            }
            for content, score, domain in top_results
        ]
        
        result = {
            "domains_searched": domain_list,
            "total_found": len(results),
            "top_k_returned": len(formatted),
            "documents": formatted
        }
        
        for doc in formatted:
            _retrieved_context[doc["domain"]] = formatted
        
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "documents": []})

@tool
def analyze_retrieved_documents(documents_json: str, query: str) -> str:
    """
    Analyze retrieved documents to determine if more information is needed.
    Helps agent reason about whether to retrieve more documents.
    
    Args:
        documents_json: JSON string of retrieved documents
        query: Original user query
        
    Returns:
        Analysis with suggestions for additional retrieval if needed
    """
    try:
        docs = json.loads(documents_json)
        doc_list = docs.get("documents", [])
        
        if not doc_list:
            return json.dumps({
                "sufficient": False,
                "reason": "No documents retrieved",
                "recommendation": "Try broader search terms or check all domains"
            })
        
        avg_score = sum(d.get("score", 0) for d in doc_list) / len(doc_list)
        
        analysis = {
            "sufficient": avg_score > 0.3 and len(doc_list) >= 3,
            "doc_count": len(doc_list),
            "avg_relevance": round(avg_score, 4),
            "recommendation": (
                "Sufficient context" if avg_score > 0.3 and len(doc_list) >= 3
                else "Retrieve more documents from different domains or refine search"
            )
        }
        return json.dumps(analysis)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def synthesize_answer(context_json, query: str) -> str:
    """
    Synthesize final answer from retrieved context.
    This is the final step - formats answer based on retrieved docs.
    
    Args:
        context_json: JSON string or dict with all relevant documents
        query: Original query
        
    Returns:
        Synthesized answer based on context
    """
    try:
        # Handle both string and dict inputs
        if isinstance(context_json, str):
            context = json.loads(context_json)
        else:
            context = context_json
            
        docs = context.get("documents", [])
        
        if not docs:
            return "No relevant information found in knowledge base. Please try a different question."
        
        context_text = "\n".join([
            f"[{doc.get('domain', 'N/A').upper()}] {doc.get('content', '')}"
            for doc in docs
        ])
        
        prompt = f"""Based on ONLY the following context, answer the user's question.
Do NOT invent information. If answer is not in context, say so.

CONTEXT:
{context_text}

USER QUESTION: {query}

ANSWER:"""
        
        message = HumanMessage(content=prompt)
        response = llm.invoke([message])
        return response.content
    except Exception as e:
        return f"Error synthesizing answer: {str(e)}"


# ============================================================================
# AGENTIC ORCHESTRATOR - ReAct Pattern
# ============================================================================

class AgricultureOrchestratorAgent:
    """
    True agentic orchestrator using ReAct (Reasoning + Acting) pattern with conversation memory.
    
    Features:
    1. Agent reasons about what information is needed
    2. Decides which tools to call (analyze intent, retrieve from domains, etc.)
    3. Observes tool outputs
    4. Iteratively refines search strategy based on results
    5. Synthesizes final answer when sufficient context is gathered
    6. Maintains conversation history across multiple turns
    7. Stores all interactions in database for persistence and analytics
    
    This is a real thinking agent with memory, not just a pipeline.
    """
    
    def __init__(self, max_iterations: int = 15, session_id: str = None, 
                 chat_title: str = None):
        self.llm_with_tools = llm
        self.max_iterations = max_iterations
        self.agent_executor = None
        
        # Initialize conversation history manager with Supabase
        self.history_manager = ConversationHistoryManager(session_id=session_id)
        
        # Set chat title if provided
        if chat_title:
            self.history_manager.create_chat(chat_title, f"Agriculture discussion - {datetime.now().isoformat()}")
        
        self._setup_agent()
    
    def _setup_agent(self):
        """Set up the agent with tool-calling capabilities and conversation memory"""
        tools = [
            analyze_query_intent,
            retrieve_documents_from_domain,
            retrieve_multi_domain_documents,
            analyze_retrieved_documents,
            synthesize_answer,
        ]
        
        # System prompt with context awareness
        system_prompt = """You are an agricultural knowledge agent. Answer questions efficiently using available tools.

TASK WORKFLOW:
1. Call analyze_query_intent to determine relevant domains
2. Call retrieve_documents_from_domain or retrieve_multi_domain_documents based on intent
3. If documents look sufficient (avg score > 0.3 and count >= 3), call synthesize_answer
4. If documents are insufficient, try alternative domain searches or refine keywords, then synthesize

KEY RULES:
- Be concise and direct in your reasoning
- Make maximum 2-3 tool calls before synthesizing the answer
- Ground all answers in retrieved documents - do not invent facts
- Use conversation history to avoid repetition
- When done gathering information, immediately call synthesize_answer
- Do not over-iterate or make redundant tool calls"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_tool_calling_agent(self.llm_with_tools, tools, prompt)
        
        # Create executor with max iterations
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=self.max_iterations,
            early_stopping_method="force"  # Force stop after max iterations
        )
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process query using agentic reasoning loop with conversation history.
        
        The agent will:
        - Use conversation history as context
        - Reason about what tools to use
        - Execute tools adaptively
        - Refine approach based on results
        - Generate final answer with reasoning
        - Store query and response in database
        
        Args:
            user_query: The user's question
            
        Returns:
            Dict with final answer, reasoning trace, and metadata
        """
        import time
        start_time = time.time()
        
        print(f"\n{'='*70}")
        print(f"🤖 AGRICULTURE ORCHESTRATOR AGENT (WITH CONVERSATION MEMORY)")
        print(f"{'='*70}\n")
        print(f"📝 Query: {user_query}\n")
        
        # Show conversation context if available
        recent_context = self.history_manager.get_recent_context(last_n=2)
        if recent_context:
            print(f"💭 Recent Context:")
            print(f"{recent_context}\n")
        
        print(f"🧠 Agent is thinking and reasoning about your question...\n")
        print(f"{'='*70}\n")
        
        try:
            # Add user message to history
            self.history_manager.add_user_message(user_query)
            
            # Get conversation history for agent context
            chat_history = self.history_manager.get_message_history()[-6:]  # Last 3 turns
            
            # Run the agent with reasoning loop and conversation history
            result = self.agent_executor.invoke({
                "input": user_query,
                "chat_history": chat_history
            })
            
            final_output = result.get("output", "")
            
            # Add agent response to history
            self.history_manager.add_agent_response(final_output, {
                "type": "response",
                "iteration_count": len(result.get("intermediate_steps", []))
            })
            
            print(f"\n{'='*70}")
            print(f"📋 FINAL ANSWER")
            print(f"{'='*70}\n")
            print(final_output)
            print(f"\n{'='*70}\n")
            
            # Extract metadata from tools
            domains_searched = list(_retrieved_context.keys())
            duration = time.time() - start_time
            
            # Save to database
            self.history_manager.save_query_response(
                query=user_query,
                response=final_output,
                domains=domains_searched if domains_searched else ["multiple"],
                duration=duration,
                status="success"
            )
            
            return {
                "status": "success",
                "answer": final_output,
                "reasoning": "Agent used multi-step reasoning with tool calls to gather and synthesize information",
                "metadata": {
                    "domains_searched": domains_searched if domains_searched else ["multiple"],
                    "duration_seconds": round(duration, 2),
                    "session_id": self.history_manager.session_id,
                }
            }
        
        except Exception as e:
            error_message = str(e)
            print(f"\n❌ Agent Error: {error_message}\n")

            # Fallback: if tool-calling failed but we already have retrieved context,
            # synthesize an answer directly to avoid a hard failure.
            if "Failed to call a function" in error_message and _retrieved_context:
                fallback_docs = []
                for domain, docs in _retrieved_context.items():
                    for doc in docs:
                        fallback_docs.append({
                            "domain": domain,
                            "content": doc.get("content", ""),
                            "score": doc.get("score", 0),
                        })

                fallback_answer = synthesize_answer({"documents": fallback_docs}, user_query)
                duration = time.time() - start_time

                self.history_manager.save_query_response(
                    query=user_query,
                    response=fallback_answer,
                    domains=list(_retrieved_context.keys()),
                    duration=duration,
                    status="success"
                )

                return {
                    "status": "success",
                    "answer": fallback_answer,
                    "reasoning": "Fallback synthesis after tool-call failure",
                    "metadata": {
                        "domains_searched": list(_retrieved_context.keys()),
                        "duration_seconds": round(duration, 2),
                        "session_id": self.history_manager.session_id,
                    }
                }
            
            # Save error to database
            duration = time.time() - start_time
            self.history_manager.save_query_response(
                query=user_query,
                response=error_message,
                domains=[],
                duration=duration,
                status="error"
            )
            
            return {
                "status": "error",
                "answer": f"Agent encountered an error: {error_message}",
                "reasoning": error_message,
                "metadata": {"session_id": self.history_manager.session_id}
            }
    
    def get_chat_summary(self) -> Dict:
        """Get summary of current chat session"""
        return self.history_manager.get_chat_summary()
    
    def export_chat(self, output_file: str = None) -> str:
        """Export conversation chat to JSON file"""
        return self.history_manager.export_chat(output_file)


# ============================================================================
# MAIN EXECUTION WITH CHAT MANAGEMENT
# ============================================================================

def show_main_menu():
    """Show main menu"""
    print("\n" + "="*70)
    print("🌾 ZARAI RADAR - MAIN MENU")
    print("="*70)
    print("\nOptions:")
    print("  1. Start new chat conversation")
    print("  2. Resume existing chat")
    print("  3. View all chats")
    print("  4. Search chats")
    print("  5. Delete chat")
    print("  6. Exit")
    
    choice = input("\nChoose option (1-6): ").strip()
    return choice

def show_chat_list():
    """Display list of previous chats with titles"""
    try:
        history_mgr = ConversationHistoryManager()
        chats = history_mgr.list_chats(limit=20)
        
        if not chats:
            print("\n⚠️  No previous chats found.\n")
            return None
        
        print("\n" + "="*70)
        print("📚 YOUR CONVERSATIONS")
        print("="*70 + "\n")
        
        for i, chat in enumerate(chats, 1):
            print(f"{i}. 💬 {chat['chat_title']}")
            print(f"   ID: {chat['session_id']}")
            print(f"   Created: {chat['created_at']}")
            print(f"   Queries: {chat['query_count']}")
            if chat['description']:
                print(f"   Description: {chat['description']}")
            print()
        
        return chats
    except Exception as e:
        print(f"❌ Error listing chats: {str(e)}")
        return None

def create_new_chat():
    """Create a new chat with title"""
    print("\n" + "="*70)
    print("➕ CREATE NEW CHAT")
    print("="*70 + "\n")
    
    chat_title = input("Enter chat title (e.g., 'Cotton Growing Guide'): ").strip()
    if not chat_title:
        print("❌ Chat title cannot be empty")
        return None
    
    description = input("Enter chat description (optional): ").strip()
    
    # Create agent with new chat
    agent = AgricultureOrchestratorAgent(chat_title=chat_title)
    if description:
        agent.history_manager.chat_title = chat_title
    
    print(f"\n✓ New chat created: '{chat_title}'")
    print(f"  Session ID: {agent.history_manager.session_id}\n")
    
    return agent

def load_existing_chat():
    """Load and resume existing chat"""
    chats = show_chat_list()
    if not chats:
        return None
    
    choice = input("Enter chat number to load (or 'cancel'): ").strip()
    if choice.lower() == 'cancel':
        return None
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(chats):
            session_id = chats[idx]['session_id']
            agent = AgricultureOrchestratorAgent(session_id=session_id)
            if agent.history_manager.load_chat(session_id):
                return agent
    except (ValueError, IndexError):
        pass
    
    print("❌ Invalid selection")
    return None

def search_chats_menu():
    """Search for chats"""
    print("\n" + "="*70)
    print("🔍 SEARCH CHATS")
    print("="*70 + "\n")
    
    keyword = input("Enter search keyword: ").strip()
    if not keyword:
        return
    
    try:
        history_mgr = ConversationHistoryManager()
        results = history_mgr.search_chats(keyword)
        
        if not results:
            print(f"\n⚠️  No chats found matching '{keyword}'")
            return
        
        print(f"\n📊 Found {len(results)} chat(s):\n")
        for i, chat in enumerate(results, 1):
            print(f"{i}. 💬 {chat['chat_title']}")
            print(f"   ID: {chat['session_id']}")
            print(f"   Updated: {chat['updated_at']}\n")
    except Exception as e:
        print(f"❌ Search error: {str(e)}")

def delete_chat_menu():
    """Delete a chat"""
    chats = show_chat_list()
    if not chats:
        return
    
    choice = input("Enter chat number to delete (or 'cancel'): ").strip()
    if choice.lower() == 'cancel':
        return
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(chats):
            session_id = chats[idx]['session_id']
            chat_title = chats[idx]['chat_title']
            
            confirm = input(f"\n⚠️  Delete chat '{chat_title}'? (yes/no): ").strip().lower()
            if confirm == 'yes':
                history_mgr = ConversationHistoryManager()
                if history_mgr.delete_chat(session_id):
                    print(f"✓ Chat deleted successfully")
    except (ValueError, IndexError):
        pass

def main():
    """Interactive interface for the agentic orchestrator with chat history"""
    
    print("\n" + "="*70)
    print("🌾 ZARAI RADAR - AGRICULTURE ORCHESTRATOR AGENT")
    print("WITH POSTGRESQL CONVERSATION MEMORY & CHAT TITLES")
    print("="*70)
    print("\nSystem Features:")
    print("  ✓ ReAct-based reasoning agent (think → act → observe)")
    print("  ✓ Multi-step tool orchestration")
    print("  ✓ Adaptive search strategy based on results")
    print("  ✓ CHAT HISTORY with titles")
    print("  ✓ POSTGRESQL PERSISTENCE")
    print("  ✓ Resume chats anytime")
    print("  ✓ Search & manage chats")
    print("  ✓ Multi-domain knowledge integration")
    print("\nPowered by:")
    print("  - GROK LLM with tool-calling")
    print("  - pgvector semantic search")
    print("  - PostgreSQL for persistence")
    print("  - Domain intent detection (Disease, Climate, Soil, Policy)")
    print("="*70 + "\n")
    
    agent = None
    
    while True:
        try:
            if agent is None:
                choice = show_main_menu()
                
                if choice == "1":
                    # Create new chat
                    agent = create_new_chat()
                
                elif choice == "2":
                    # Load existing chat
                    agent = load_existing_chat()
                
                elif choice == "3":
                    # View all chats
                    show_chat_list()
                
                elif choice == "4":
                    # Search chats
                    search_chats_menu()
                
                elif choice == "5":
                    # Delete chat
                    delete_chat_menu()
                
                elif choice == "6":
                    print("\nThank you for using Zarai Radar! 🌾\n")
                    break
                else:
                    print("⚠️  Invalid choice. Please try again.")
            
            else:
                # Chat conversation loop
                print(f"\n{'='*70}")
                print(f"💬 CHAT: {agent.history_manager.chat_title}")
                print(f"{'='*70}\n")
                
                query = input("🌾 Ask your question (or type 'menu'/'export'/'quit'):\n> ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("\nThank you for using Zarai Radar! 🌾\n")
                    break
                
                elif query.lower() == 'menu':
                    # Show chat summary and return to menu
                    summary = agent.get_chat_summary()
                    print(f"\n{'='*70}")
                    print(f"📊 CHAT SUMMARY")
                    print(f"{'='*70}")
                    print(f"Title: {summary['chat_title']}")
                    print(f"ID: {summary['session_id']}")
                    print(f"Total Messages: {summary['message_count']}")
                    print(f"User Queries: {summary['user_queries']}")
                    print(f"Agent Responses: {summary['agent_responses']}")
                    print(f"Created: {summary['created_at']}")
                    print(f"Query Count: {summary['query_count']}\n")
                    agent = None
                
                elif query.lower() == 'export':
                    # Export chat to JSON
                    agent.export_chat()
                
                elif not query:
                    print("⚠️  Please enter a valid question.")
                    continue
                
                else:
                    # Process query with conversation history
                    result = agent.process_query(query)
                    
                    # Show metadata
                    if result["status"] == "success":
                        metadata = result.get("metadata", {})
                        print(f"\n📌 Query Information:")
                        print(f"   Chat: {agent.history_manager.chat_title}")
                        print(f"   Domains: {', '.join(metadata.get('domains_searched', ['N/A']))}")
                        print(f"   Duration: {metadata.get('duration_seconds', 0):.2f}s\n")
        
        except KeyboardInterrupt:
            print("\n\nThank you for using Zarai Radar! 🌾\n")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            print("Please try again.\n")


if __name__ == "__main__":
    agent = AgricultureOrchestratorAgent()
