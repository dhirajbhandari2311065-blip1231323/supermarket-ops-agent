import os
import json
import logging
from typing import Any, Dict, List, Optional
from google.genai import types
from google.genai.errors import APIError
from openai import AsyncOpenAI

from app.agent.session import session_manager
from app.tools.executor import ToolExecutor
from app.tools.schemas import agent_tools
from app.agent.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def convert_gemini_tools_to_openai(tools_list: List[Any]) -> List[Dict[str, Any]]:
    """Converts Google GenAI types.Tool objects or FunctionDeclarations to OpenAI tool call format for Groq."""
    openai_tools = []
    
    for tool_container in tools_list:
        # Check if the item is wrapped in types.Tool(function_declarations=[...])
        if hasattr(tool_container, "function_declarations") and tool_container.function_declarations:
            declarations = tool_container.function_declarations
        elif isinstance(tool_container, list):
            declarations = tool_container
        else:
            declarations = [tool_container]

        for decl in declarations:
            name = getattr(decl, "name", None)
            description = getattr(decl, "description", "") or ""
            parameters = getattr(decl, "parameters", None)
            
            param_dict = {"type": "object", "properties": {}}
            
            if parameters:
                if hasattr(parameters, "model_dump"):
                    param_dict = parameters.model_dump()
                elif hasattr(parameters, "to_dict"):
                    param_dict = parameters.to_dict()
                elif isinstance(parameters, dict):
                    param_dict = parameters

            openai_tools.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": param_dict
                }
            })
            
    return openai_tools


class AgentOrchestrator:
    def __init__(self, gemini_client):
        self.gemini_client = gemini_client
        self.gemini_model = "gemini-3.6-flash"
        
        # Initialize Groq client
        groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_client = (
            AsyncOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_api_key
            )
            if groq_api_key
            else None
        )
        self.groq_model = "llama-3.3-70b-versatile"
        self._converted_groq_tools = convert_gemini_tools_to_openai(agent_tools)

    async def process_user_message(self, chat_id: int, db_session: Any, user_text: str) -> str:
        """Processes user input with automatic failover from Gemini to Groq."""
        active_bill_id = session_manager.get_active_bill(chat_id)
        
        context_prefix = ""
        if active_bill_id:
            context_prefix = f"[SYSTEM CONTEXT: ACTIVE_DRAFT_BILL_ID = {active_bill_id}]\n"
            
        full_prompt = f"{context_prefix}User message: {user_text}"

        # 1. Primary Attempt: Google Gemini
        try:
            return await self._run_gemini_loop(chat_id, db_session, full_prompt)
        except Exception as e:
            logger.warning(
                f"Gemini execution failed ({type(e).__name__}: {e}). Initiating Groq failover..."
            )
            
            # 2. Fallback Attempt: Groq (Llama 3.3 70B)
            if self.groq_client:
                try:
                    return await self._run_groq_fallback(chat_id, db_session, full_prompt)
                except Exception as groq_err:
                    logger.error(f"Groq failover also failed: {groq_err}")
                    raise groq_err
            else:
                raise e

    async def _run_gemini_loop(self, chat_id: int, db_session: Any, prompt: str) -> str:
        """Standard Gemini Tool Call Loop using async execution."""
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=agent_tools,
            temperature=0.2
        )

        for iteration in range(5):
            # Async generation call to Gemini API
            response = await self.gemini_client.aio.models.generate_content(
                model=self.gemini_model,
                contents=contents,
                config=config
            )

            function_calls = getattr(response, "function_calls", None)
            if not function_calls:
                return response.text or "Done."

            # Append the assistant's response containing tool execution request
            if hasattr(response, "candidates") and response.candidates:
                contents.append(response.candidates[0].content)

            tool_response_parts = []
            for call in function_calls:
                tool_name = call.name
                tool_args = dict(call.args) if call.args else {}
                
                logger.info(f"[Gemini] Tool Execution (Turn {iteration+1}): {tool_name}({tool_args})")

                tool_result = await ToolExecutor.execute_tool(
                    db_session, chat_id, tool_name, tool_args
                )

                # Keep session active bill ID updated if affected
                self._handle_bill_session_updates(chat_id, tool_name, tool_result)

                tool_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"result": tool_result}
                    )
                )

            contents.append(types.Content(role="user", parts=tool_response_parts))

        return "Task completed."

    async def _run_groq_fallback(self, chat_id: int, db_session: Any, prompt: str) -> str:
        """Groq Failover Execution Loop using Llama 3.3 70B."""
        logger.info("[Fallback] Executing failover to Groq (llama-3.3-70b-versatile)...")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        for iteration in range(5):
            response = await self.groq_client.chat.completions.create(
                model=self.groq_model,
                messages=messages,
                tools=self._converted_groq_tools if self._converted_groq_tools else None,
                tool_choice="auto",
                temperature=0.2
            )

            msg = response.choices[0].message
            
            # Format assistant message for conversion
            assistant_msg = {"role": "assistant", "content": msg.content}
            if msg.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in msg.tool_calls
                ]
            
            messages.append(assistant_msg)

            if not msg.tool_calls:
                return msg.content or "Done via Groq."

            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except Exception:
                    tool_args = {}

                logger.info(f"[Groq] Tool Execution (Turn {iteration+1}): {tool_name}({tool_args})")

                tool_result = await ToolExecutor.execute_tool(
                    db_session, chat_id, tool_name, tool_args
                )

                # Keep session active bill ID updated if affected
                self._handle_bill_session_updates(chat_id, tool_name, tool_result)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result)
                })

        return "Task completed via Groq."

    def _handle_bill_session_updates(self, chat_id: int, tool_name: str, tool_result: Dict[str, Any]) -> None:
        """Helper to sync bill state mutations with session_manager."""
        if not isinstance(tool_result, dict):
            return

        if tool_name == "update_bill_item" and tool_result.get("status") == "success":
            new_bill_id = tool_result.get("bill_id")
            if new_bill_id:
                session_manager.set_active_bill(chat_id, new_bill_id)

        elif tool_name == "finalize_bill" and tool_result.get("status") == "success":
            session_manager.set_active_bill(chat_id, None)