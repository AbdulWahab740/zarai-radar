# main.py
# Main entry point for Zarai Radar - Agriculture Orchestrator RAG System
import sys
import os
sys.path.insert(1, os.path.dirname(__file__))

from RAG.orchestrator_agent import main as run_orchestrator

if __name__ == "__main__":
    # Run the new orchestrator agent with multiple domains
    run_orchestrator()
