"""LangGraph workflow for the multi-agent chatbot system"""
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from .state import ChatbotState, AgentState
from .agents import MasterAgent, QueryAgent, BuyAgent, ReturnAgent, CreditAgent

class ChatbotWorkflow:
    """Main workflow orchestrator using LangGraph"""
    
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        
        # Initialize agents
        self.master_agent = MasterAgent(openai_api_key)
        self.query_agent = QueryAgent(openai_api_key)
        self.buy_agent = BuyAgent(openai_api_key)
        self.return_agent = ReturnAgent(openai_api_key)
        self.credit_agent = CreditAgent(openai_api_key)
        
        # Build the workflow graph
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        
        # Define the state graph
        workflow = StateGraph(ChatbotState)
        
        # Add nodes for each agent
        workflow.add_node("master", self._master_node)
        workflow.add_node("query", self._query_node)
        workflow.add_node("buy", self._buy_node)
        workflow.add_node("return", self._return_node)
        workflow.add_node("credit", self._credit_node)
        
        # Set entry point
        workflow.add_edge(START, "master")
        
        # Add conditional edges from master to other agents
        workflow.add_conditional_edges(
            "master",
            self._route_from_master,
            {
                "query": "query",
                "buy": "buy", 
                "return": "return",
                "credit": "credit",
                "end": END
            }
        )
        
        # All subordinate agents return to master
        workflow.add_edge("query", "master")
        workflow.add_edge("buy", "master")
        workflow.add_edge("return", "master")
        workflow.add_edge("credit", "master")
        
        return workflow.compile()
    
    def _master_node(self, state: ChatbotState) -> ChatbotState:
        """Master agent node"""
        return self.master_agent.process(state)
    
    def _query_node(self, state: ChatbotState) -> ChatbotState:
        """Query agent node"""
        return self.query_agent.process(state)
    
    def _buy_node(self, state: ChatbotState) -> ChatbotState:
        """Buy agent node"""
        return self.buy_agent.process(state)
    
    def _return_node(self, state: ChatbotState) -> ChatbotState:
        """Return agent node"""
        return self.return_agent.process(state)
    
    def _credit_node(self, state: ChatbotState) -> ChatbotState:
        """Credit agent node"""
        return self.credit_agent.process(state)
    
    def _route_from_master(self, state: ChatbotState) -> str:
        """Routing logic from master agent"""
        if state.current_agent == AgentState.MASTER:
            return "end"
        else:
            return state.current_agent.value
    
    def process_message(self, user_id: int, username: str, message: str) -> Dict[str, Any]:
        """Process a user message through the workflow"""
        
        # Create initial state
        state = ChatbotState(
            user_id=user_id,
            username=username,
            user_message=message
        )
        
        # Add user message to conversation history
        state.add_message("user", message)
        
        try:
            # Run the workflow
            final_state = self.workflow.invoke(state)
            
            # Add agent response to conversation history
            if final_state.agent_response:
                final_state.add_message("assistant", final_state.agent_response)
            
            return {
                "success": True,
                "response": final_state.agent_response,
                "current_agent": final_state.current_agent,
                "conversation_step": final_state.conversation_step,
                "conversation_history": final_state.conversation_history,
                "transaction_result": final_state.transaction_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Chatbot error: {str(e)}",
                "response": "I'm sorry, I encountered an error. Please try again."
            }
    
    def get_welcome_message(self, username: str) -> str:
        """Get welcome message for new users"""
        return f"""👋 **Welcome to the Book Store, {username}!**

I'm your personal book assistant. I can help you with:

🔍 **query** - Search for books in our catalog
💰 **buy** - Purchase books (20 credits per book)
📚 **return** - Return books for refund
💳 **buy credits** - Add more credits to your account

Please type one of the four commands above to get started!"""