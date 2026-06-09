"""
LangGraph Multi-Agent Workflow for Support Ticket Triage.

This implements a multi-agent orchestration for ticket resolution.
Nodes:
- Classifier: Determines category, intent, sentiment, priority.
- RAG Agent: Retrieves context from similar tickets and KB.
- Responder: Generates the actual response and determines if it requires human escalation.
"""

import uuid
from typing import Any, Dict, Optional, TypedDict

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.factory import get_ai_provider
from app.repositories.ticket import TicketRepository
from app.repositories.team import TeamRepository
from app.services.rag_service import RAGService
from app.core.logging import get_logger

logger = get_logger("langgraph_workflow")

# Define the State
class TriageState(TypedDict):
    ticket_id: str
    title: str
    description: str
    customer_tier: str
    
    # Outputs from Classifier
    category: Optional[str]
    priority: Optional[str]
    sentiment_label: Optional[str]
    sentiment_score: Optional[float]
    confidence: Optional[float]
    
    # Outputs from RAG
    rag_context: Optional[str]
    
    # Outputs from Responder
    ai_summary: Optional[str]
    ai_response: Optional[str]
    requires_escalation: bool
    
    # Routing
    team_id: Optional[str]

class TicketTriageGraph:
    """Manages the LangGraph orchestration for ticket processing."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = get_ai_provider()
        self.ticket_repo = TicketRepository(db)
        self.team_repo = TeamRepository(db)
        self.rag_service = RAGService(db, self.provider)
        self.graph = self._build_graph()
        
    def _build_graph(self):
        workflow = StateGraph(TriageState)
        
        workflow.add_node("classifier", self.node_classifier)
        workflow.add_node("rag_agent", self.node_rag)
        workflow.add_node("responder", self.node_responder)
        
        # Edge Logic
        workflow.add_edge(START, "classifier")
        workflow.add_edge("classifier", "rag_agent")
        workflow.add_edge("rag_agent", "responder")
        workflow.add_edge("responder", END)
        
        return workflow.compile()

    async def node_classifier(self, state: TriageState) -> dict:
        """Classify category, intent, sentiment and priority."""
        logger.info("LangGraph: Running Classifier Node")
        
        try:
            # Re-using the abstract provider methods for classification
            classification = await self.provider.classify_ticket(
                title=state["title"],
                description=state["description"],
            )
            
            category_str = classification.category if classification else "general_inquiry"
            
            priority_result = await self.provider.predict_priority(
                title=state["title"],
                description=state["description"],
                category=category_str,
                customer_tier=state.get("customer_tier", "standard")
            )
            
            # Summarize early here to save a node
            summary_result = await self.provider.summarize_ticket(
                title=state["title"],
                description=state["description"]
            )
            
            return {
                "category": category_str,
                "confidence": classification.confidence if classification else 0.5,
                "priority": priority_result.priority if priority_result else "medium",
                "sentiment_label": priority_result.sentiment_label if priority_result else "neutral",
                "sentiment_score": priority_result.sentiment_score if priority_result else 0.5,
                "ai_summary": summary_result.summary if summary_result else ""
            }
        except Exception as e:
            logger.error(f"Classifier node failed: {e}")
            return {"category": "general_inquiry", "priority": "medium", "requires_escalation": True}

    async def node_rag(self, state: TriageState) -> dict:
        """Retrieve contextual info from KB and past tickets."""
        logger.info("LangGraph: Running RAG Agent Node")
        try:
            query_text = f"{state['title']}\n\n{state['description']}"
            contexts = await self.rag_service.retrieve_context(
                query=query_text,
                limit=5,
                threshold=0.70,
                exclude_ticket_id=uuid.UUID(state["ticket_id"])
            )
            rag_context_str = self.rag_service.format_context_for_prompt(contexts)
            return {"rag_context": rag_context_str}
        except Exception as e:
            logger.error(f"RAG node failed: {e}")
            return {"rag_context": ""}

    async def node_responder(self, state: TriageState) -> dict:
        """Generate response based on ticket info and RAG context."""
        logger.info("LangGraph: Running Responder Node")
        try:
            response_result = await self.provider.generate_response(
                title=state["title"],
                description=state["description"],
                category=state.get("category", "general_inquiry"),
                priority=state.get("priority", "medium"),
                similar_tickets=state.get("rag_context", "")
            )
            
            escalate = False
            if state.get("sentiment_label") == "frustrated" or state.get("priority") in ["high", "critical"]:
                escalate = True
                
            return {
                "ai_response": response_result.response,
                "requires_escalation": escalate
            }
        except Exception as e:
            logger.error(f"Responder node failed: {e}")
            return {"ai_response": "We will get back to you shortly.", "requires_escalation": True}

    async def run_triage(self, ticket_id: uuid.UUID) -> dict[str, Any]:
        """Entrypoint for the workflow."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)
        if not ticket:
            return {"error": "Ticket not found"}
            
        initial_state = TriageState(
            ticket_id=str(ticket_id),
            title=ticket.title,
            description=ticket.description,
            customer_tier=ticket.customer_user.customer_tier if ticket.customer_user else "standard",
            category=None, priority=None, sentiment_label=None, sentiment_score=None,
            confidence=None, rag_context=None, ai_summary=None, ai_response=None,
            requires_escalation=False, team_id=None
        )
        
        final_state = await self.graph.ainvoke(initial_state)
        
        # Determine routing team
        team_id = None
        if final_state.get("category"):
            try:
                team = await self.team_repo.get_team_for_category(final_state["category"])
                if team:
                    team_id = str(team.id)
            except Exception:
                pass
                
        # Generate and save embedding (done synchronously here or later)
        try:
            embed_text = f"{ticket.title}\n\n{ticket.description}"
            embedding_result = await self.provider.generate_embedding(embed_text)
            await self.ticket_repo.update_embedding(ticket_id, embedding_result.embedding)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
        
        # Persist results to DB
        update_data = {
            "is_triaged": True,
            "predicted_category": final_state.get("category"),
            "category_confidence": final_state.get("confidence"),
            "predicted_priority": final_state.get("priority"),
            "sentiment_score": final_state.get("sentiment_score"),
            "sentiment_label": final_state.get("sentiment_label"),
            "ai_summary": final_state.get("ai_summary"),
            "ai_response": final_state.get("ai_response"),
            "assigned_team_id": team_id
        }
        
        # Append sentiment history
        current_history = ticket.sentiment_history or []
        if final_state.get("sentiment_score"):
            current_history.append({"score": final_state["sentiment_score"], "label": final_state["sentiment_label"], "source": "initial_triage"})
            update_data["sentiment_history"] = current_history
            
        await self.ticket_repo.update(ticket_id, **{k: v for k, v in update_data.items() if v is not None})
        
        return final_state
