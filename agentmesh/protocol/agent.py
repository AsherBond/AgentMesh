import json
import time

from agentmesh.common.utils import string_util
from agentmesh.common.utils.log import logger
from agentmesh.models import LLMRequest, LLMModel
from agentmesh.protocol.agent_stream import AgentStreamExecutor
from agentmesh.protocol.context import TeamContext, AgentOutput
from agentmesh.protocol.result import AgentAction, AgentActionType, ToolResult, AgentResult
from agentmesh.tools.base_tool import BaseTool
from agentmesh.tools.base_tool import ToolStage


class Agent:
    def __init__(self, name: str, system_prompt: str, description: str, model: LLMModel = None, team_context=None,
                 tools=None, output_mode="print", max_steps=100, max_context_tokens=None, context_reserve_tokens=None):
        """
        Initialize the Agent with a name, system prompt, model, description, and optional group context.

        :param name: The name of the agent.
        :param system_prompt: The system prompt for the agent.
        :param model: An instance of LLMModel to be used by the agent.
        :param description: A description of the agent.
        :param team_context: Optional reference to the group context.
        :param tools: Optional list of tools for the agent to use.
        :param output_mode: Control how execution progress is displayed: 
                           "print" for console output or "logger" for using logger
        :param max_steps: Maximum number of steps the agent can take (default: 100)
        :param max_context_tokens: Maximum tokens to keep in context (default: None, auto-calculated based on model)
        :param context_reserve_tokens: Reserve tokens for new requests (default: None, auto-calculated)
        """
        self.name = name
        self.system_prompt = system_prompt
        self.model: LLMModel = model  # Instance of LLMModel
        self.description = description
        self.team_context: TeamContext = team_context  # Store reference to group context if provided
        self.subtask: str = ""
        self.tools: list = []
        self.max_steps = max_steps  # max ReAct steps, default 100
        self.max_context_tokens = max_context_tokens  # max tokens in context
        self.context_reserve_tokens = context_reserve_tokens  # reserve tokens for new requests
        self.conversation_history = []
        self.action_history = []
        self.captured_actions = []  # Initialize captured actions list
        self.ext_data = ""
        self.output_mode = output_mode
        self.last_usage = None  # Store last API response usage info
        self.messages = []  # Unified message history for stream mode
        if tools:
            for tool in tools:
                self.add_tool(tool)

    def add_tool(self, tool: BaseTool):
        """
        Add a tool to the agent.

        :param tool: The tool to add (either a tool instance or a tool name)
        """
        # If tool is already an instance, use it directly
        tool.model = self.model
        self.tools.append(tool)

    def _get_model_context_window(self) -> int:
        """
        Get the model's context window size in tokens.
        Auto-detect based on model name.
        
        Model context windows:
        - Claude 3.5/3.7 Sonnet: 200K tokens
        - Claude 3 Opus: 200K tokens
        - GPT-4 Turbo/128K: 128K tokens
        - GPT-4: 8K-32K tokens
        - GPT-3.5: 16K tokens
        - DeepSeek: 64K tokens
        
        :return: Context window size in tokens
        """
        if self.model and hasattr(self.model, 'model'):
            model_name = self.model.model.lower()

            # Claude models - 200K context
            if 'claude-3' in model_name or 'claude-sonnet' in model_name:
                return 200000

            # GPT-4 models
            elif 'gpt-4' in model_name:
                if 'turbo' in model_name or '128k' in model_name:
                    return 128000
                elif '32k' in model_name:
                    return 32000
                else:
                    return 8000

            # GPT-3.5
            elif 'gpt-3.5' in model_name:
                if '16k' in model_name:
                    return 16000
                else:
                    return 4000

            # DeepSeek
            elif 'deepseek' in model_name:
                return 64000

        # Default conservative value
        return 10000

    def _get_context_reserve_tokens(self) -> int:
        """
        Get the number of tokens to reserve for new requests.
        This prevents context overflow by keeping a buffer.
        
        :return: Number of tokens to reserve
        """
        if self.context_reserve_tokens is not None:
            return self.context_reserve_tokens

        # Reserve ~20% of context window for new requests
        context_window = self._get_model_context_window()
        return max(4000, int(context_window * 0.2))

    def _estimate_message_tokens(self, message: dict) -> int:
        """
        Estimate token count for a message using chars/4 heuristic.
        This is a conservative estimate (tends to overestimate).

        :param message: Message dict with 'role' and 'content'
        :return: Estimated token count
        """
        content = message.get('content', '')
        if isinstance(content, str):
            return max(1, len(content) // 4)
        elif isinstance(content, list):
            # Handle multi-part content (text + images)
            total_chars = 0
            for part in content:
                if isinstance(part, dict) and part.get('type') == 'text':
                    total_chars += len(part.get('text', ''))
                elif isinstance(part, dict) and part.get('type') == 'image':
                    # Estimate images as ~1200 tokens
                    total_chars += 4800
            return max(1, total_chars // 4)
        return 1

    def _calculate_context_tokens(self) -> int:
        """
        Calculate total context tokens from conversation history.
        Uses last API response usage if available, otherwise estimates.

        Strategy (similar to pi-mono):
        1. If we have usage info from last API call, use those actual tokens
        2. For any messages added after that, estimate their tokens
        3. Sum them up for total context tokens

        :return: Total estimated context tokens
        """
        if not self.conversation_history:
            return 0

        # If we have usage info from last API call, use it as base
        if self.last_usage:
            usage_tokens = (
                    self.last_usage.get('prompt_tokens', 0) +
                    self.last_usage.get('completion_tokens', 0)
            )
            # Note: In real implementation, we'd track which messages were included
            # in that API call. For simplicity, we'll just use the usage as baseline
            return usage_tokens

        # Otherwise, estimate all messages
        total_tokens = 0
        for msg in self.conversation_history:
            total_tokens += self._estimate_message_tokens(msg)

        return total_tokens

    def _trim_conversation_history(self):
        """
        Trim conversation history to stay within token limits.
        Uses actual token counts when available, falls back to estimation.
        
        Strategy:
        1. Calculate current context tokens
        2. If exceeds (context_window - reserve_tokens), trim oldest messages
        3. Always keep system message
        4. Remove messages from oldest until we're under the limit
        """
        if not self.conversation_history:
            return

        context_window = self._get_model_context_window()
        reserve_tokens = self._get_context_reserve_tokens()
        max_tokens = context_window - reserve_tokens

        current_tokens = self._calculate_context_tokens()

        # If we're under the limit, no need to trim
        if current_tokens <= max_tokens:
            return

        # Separate system messages from others
        system_messages = []
        other_messages = []

        for msg in self.conversation_history:
            if msg.get('role') == 'system':
                system_messages.append(msg)
            else:
                other_messages.append(msg)

        # Calculate system message tokens
        system_tokens = sum(self._estimate_message_tokens(msg) for msg in system_messages)

        # Calculate how many tokens we can keep for other messages
        available_tokens = max_tokens - system_tokens

        # Keep messages from newest, accumulating tokens
        kept_messages = []
        accumulated_tokens = 0

        for msg in reversed(other_messages):
            msg_tokens = self._estimate_message_tokens(msg)
            if accumulated_tokens + msg_tokens <= available_tokens:
                kept_messages.insert(0, msg)
                accumulated_tokens += msg_tokens
            else:
                # Stop when we exceed the limit
                break

        # Rebuild conversation history
        old_count = len(self.conversation_history)
        self.conversation_history = system_messages + kept_messages
        new_count = len(self.conversation_history)

        if old_count > new_count:
            logger.info(
                f"Context trimmed: {old_count} -> {new_count} messages "
                f"(~{current_tokens} -> ~{system_tokens + accumulated_tokens} tokens, "
                f"limit: {max_tokens})"
            )

    def _build_task_prompt(self) -> str:
        """Build the task prompt for team context (used in step() method)"""
        if not self.team_context:
            return self.subtask

        # Get the current timestamp
        timestamp = time.time()
        local_time = time.localtime(timestamp)
        formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", local_time)

        ext_data_prompt = self.ext_data if self.ext_data else ""

        prompt = f"""## Role
Your role: {self.name}
Your role description: {self.description}
You are handling the subtask as a member of the {self.team_context.name} team. Please answer in the same language as the user's original task.

## Current task context:
Current time: {formatted_time}
Team description: {self.team_context.description}

## Other agents output:
{self._fetch_agents_outputs()}

{ext_data_prompt}

## Your sub task
{self.subtask}"""

        return prompt

    def _find_tool(self, tool_name: str):
        """Find and return a tool with the specified name"""
        for tool in self.tools:
            if tool.name == tool_name:
                # Only pre-process stage tools can be actively called
                if tool.stage == ToolStage.PRE_PROCESS:
                    tool.model = self.model
                    tool.context = self  # Set tool context
                    return tool
                else:
                    # If it's a post-process tool, return None to prevent direct calling
                    logger.warning(f"Tool {tool_name} is a post-process tool and cannot be called directly.")
                    return None
        return None

    # output function based on mode
    def output(self, message="", end="\n"):
        if self.output_mode == "print":
            print(message, end=end)
        elif message:
            logger.info(message)

    def step(self):
        """
        Execute the agent's task using tool-call mode (unified with run_stream).

        This method now uses the same tool-call mechanism as run_stream(),
        providing a consistent interface across both execution modes.

        :return: A StepResult object containing the final answer and step count
        """
        # Initialize final answer (if it doesn't exist)
        if not hasattr(self, 'final_answer'):
            self.final_answer = ""

        # Print agent name and subtask
        self.output(f"🤖 {self.name.strip()}: {self.subtask}")

        # Build the task prompt
        task_prompt = self._build_task_prompt()

        # Define event handler for output_mode
        def step_event_handler(event):
            event_type = event["type"]
            data = event.get("data", {})

            if event_type == "turn_start":
                turn = data.get('turn', 0)
                # Check if team's max_steps will be exceeded
                if self.team_context and self.team_context.current_steps >= self.team_context.max_steps:
                    logger.warning(f"Team's max steps ({self.team_context.max_steps}) reached.")
                    raise Exception("Team's max steps reached")

                # Increment team's step counter
                if self.team_context:
                    self.team_context.current_steps += 1

                if self.output_mode == "print":
                    print(f"\nStep {turn}:")

            elif event_type == "message_update":
                if self.output_mode == "print":
                    print(data.get("delta", ""), end="", flush=True)

            elif event_type == "tool_execution_start":
                tool_name = data.get('tool_name')
                args = data.get('arguments', {})
                if self.output_mode == "print":
                    print(f"\n🛠️ {tool_name}: {json.dumps(args, ensure_ascii=False)}")
                else:
                    logger.info(f"🛠️ {tool_name}: {json.dumps(args, ensure_ascii=False)}")

            elif event_type == "tool_execution_end":
                status = data.get('status')
                result = data.get('result')
                if status == "error":
                    logger.error(f"Tool execution error: {result}")

            elif event_type == "error":
                logger.error(f"Error: {data.get('error')}")

        try:
            # Use run_stream with the task prompt
            final_answer = self.run_stream(
                user_message=task_prompt,
                on_event=step_event_handler,
                clear_history=True  # Each step() call is independent
            )

            self.final_answer = final_answer

            # Store the final answer in team context
            if self.team_context:
                self.team_context.agent_outputs.append(
                    AgentOutput(agent_name=self.name, output=final_answer)
                )

            # Execute all post-process tools
            self._execute_post_process_tools()

            # Calculate step count from captured actions
            step_count = len([a for a in self.captured_actions if a.action_type == AgentActionType.TOOL_USE])

            return AgentResult.success(
                final_answer=final_answer,
                step_count=step_count
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Step execution error: {error_msg}")
            return AgentResult.error(error_msg, 0)

    def _execute_post_process_tools(self):
        """Execute all post-process stage tools"""
        # Get all post-process stage tools
        post_process_tools = [tool for tool in self.tools if tool.stage == ToolStage.POST_PROCESS]

        # Execute each tool
        for tool in post_process_tools:
            # Set tool context
            tool.context = self

            # Record start time for execution timing
            start_time = time.time()

            # Execute tool (with empty parameters, tool will extract needed info from context)
            result = tool.execute({})

            # Calculate execution time
            execution_time = time.time() - start_time

            # Capture tool use for tracking
            self.capture_tool_use(
                tool_name=tool.name,
                input_params={},  # Post-process tools typically don't take parameters
                output=result.result,
                status=result.status,
                error_message=str(result.result) if result.status == "error" else None,
                execution_time=execution_time
            )

            # Log result
            if result.status == "success":
                # Print tool execution result in the desired format
                self.output(f"\n🛠️ {tool.name}: {json.dumps(result.result)}")
            else:
                # Print failure in print mode
                self.output(f"\n🛠️ {tool.name}: {json.dumps({'status': 'error', 'message': str(result.result)})}")

    def should_invoke_next_agent(self) -> int:
        """
        Determine if the next agent should be invoked based on the reply.

        :return: The ID of the next agent to invoke, or -1 if no next agent should be invoked.
        """
        # Get the model to use - use team's model
        model_to_use = self.team_context.model

        # Create a request to the model to determine if the next agent should be invoked
        # Exclude the current agent from the list to prevent self-recursion
        agents_str = ', '.join(
            f'{{"id": {i}, "name": "{agent.name}", "description": "{agent.description}", "system_prompt": "{agent.system_prompt}"}}'
            for i, agent in enumerate(self.team_context.agents)
            if agent.name != self.name  # Exclude current agent
        )

        # If no other agents are available, return -1
        if not agents_str:
            return -1

        agent_outputs_list = self._fetch_agents_outputs()

        prompt = AGENT_DECISION_PROMPT.format(group_name=self.team_context.name,
                                              group_description=self.team_context.description,
                                              current_agent_name=self.name,
                                              group_rules=self.team_context.rule,
                                              agent_outputs_list=agent_outputs_list,
                                              agents_str=agents_str,
                                              user_task=self.team_context.user_task)

        # Start loading animation
        self.output()
        loading = LoadingIndicator(message="Select agent in team...", animation_type="spinner")
        loading.start()

        # Use team's model for agent selection decision
        request = LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            json_format=True
        )

        response = model_to_use.call(request)

        # Stop loading animation
        loading.stop()
        print()

        # Check if API call was successful
        if response.is_error:
            error_message = response.get_error_msg()
            logger.error(f"Error: {error_message}")
            return -1  # If error occurs, return -1 to indicate not to call the next agent

        # Get content from successful response
        decision_text = response.data["choices"][0]["message"]["content"]
        try:
            decision_res = string_util.json_loads(decision_text)
            selected_agent_id = decision_res.get("id")

            # Check if we should stop the chain
            if selected_agent_id is None or int(selected_agent_id) < 0:
                return -1

            # Get subtask
            subtask = decision_res.get("subtask", "")

            # Map the selected agent ID to the actual agent ID
            selected_agent = self.team_context.agents[int(selected_agent_id)]

            # Set subtask for the next agent
            selected_agent.subtask = subtask

            # Return the ID of the next agent
            return int(selected_agent_id)
        except Exception as e:
            logger.error(f"Failed to determine next agent: {e}")
            return -1

    def _fetch_agents_outputs(self) -> str:
        agent_outputs_list = []
        for agent_output in self.team_context.agent_outputs:
            agent_outputs_list.append(
                f"member name: {agent_output.agent_name}\noutput content: {agent_output.output}\n\n")
        return "\n".join(agent_outputs_list)

    def capture_tool_use(self, tool_name, input_params, output, status, thought=None, error_message=None,
                         execution_time=0.0):
        """
        Capture a tool use action.
        
        :param thought: thought content
        :param tool_name: Name of the tool used
        :param input_params: Parameters passed to the tool
        :param output: Output from the tool
        :param status: Status of the tool execution
        :param error_message: Error message if the tool execution failed
        :param execution_time: Time taken to execute the tool
        """
        tool_result = ToolResult(
            tool_name=tool_name,
            input_params=input_params,
            output=output,
            status=status,
            error_message=error_message,
            execution_time=execution_time
        )

        action = AgentAction(
            agent_id=self.id if hasattr(self, 'id') else str(id(self)),
            agent_name=self.name,
            action_type=AgentActionType.TOOL_USE,
            tool_result=tool_result,
            thought=thought
        )

        self.captured_actions.append(action)

        return action

    def run_stream(self, user_message: str, on_event=None, clear_history: bool = False) -> str:
        """
        Execute single agent task with streaming (based on tool-call)

        This is a new method for single agent mode, supporting:
        - Streaming output
        - Multi-turn reasoning based on tool-call
        - Event callbacks
        - Persistent conversation history across calls

        Args:
            user_message: User message
            on_event: Event callback function callback(event: dict)
                     event = {"type": str, "timestamp": float, "data": dict}
            clear_history: If True, clear conversation history before this call (default: False)

        Returns:
            Final response text

        Example:
            # Multi-turn conversation with memory
            response1 = agent.run_stream("My name is Alice")
            response2 = agent.run_stream("What's my name?")  # Will remember Alice

            # Single-turn without memory
            response = agent.run_stream("Hello", clear_history=True)
        """
        # Clear history if requested
        if clear_history:
            self.messages = []

        # Get model to use
        model_to_use = self.model if self.model else self.team_context.model if self.team_context else None
        if not model_to_use:
            raise ValueError("No model available for agent")

        # Create stream executor with agent's message history
        executor = AgentStreamExecutor(
            agent=self,
            model=model_to_use,
            system_prompt=self.system_prompt,
            tools=self.tools,
            max_turns=self.max_steps,
            on_event=on_event,
            messages=self.messages  # Pass agent's message history
        )

        # Execute
        response = executor.run_stream(user_message)

        # Update agent's message history from executor
        self.messages = executor.messages

        return response

    def clear_history(self):
        """Clear conversation history and captured actions"""
        self.messages = []
        self.captured_actions = []
        self.conversation_history = []  # Keep for backward compatibility
        self.action_history = []  # Keep for backward compatibility


AGENT_REPLY_PROMPT = """You are part of the team, you only need to reply the part of user question related to your responsibilities

## Team
Team Name: {group_name}
Team Description: {group_description}
Team Rules: {group_rules}
Your Role: {current_agent_name}

## Team members have already output
{agent_outputs_list}

User Original Task: 
{user_task}

Your Subtask:
{subtask}"""

AGENT_DECISION_PROMPT = """## Role
You are a team decision expert, please decide whether the next member in the team is needed to complete the user task. If necessary, select the most suitable member and give the subtask that needs to be answered by this member. If not, return {{"id": -1}} directly.

## Team
Team Name: {group_name}
Team Description: {group_description}
Team Rules: {group_rules}

## List of available members:
{agents_str}

## Members have replied
{agent_outputs_list}

## Attention
1. You need to determine whether the next member is needed and which member is the most suitable based on the user's question and the rules of the team 
2. If you think the answers given by the executed members are able to answer the user's questions, return {{"id": -1}} immediately; otherwise, select the next suitable member ID and subtask content in the following JSON structure which can be parsed directly by json.loads(): 
{{"id": <member_id>, "subtask": ""}}
3. Always reply in JSON format which can be parsed directly by json.loads()

## User Original Task:
{user_task}"""
