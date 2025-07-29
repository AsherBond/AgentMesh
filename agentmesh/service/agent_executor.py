import asyncio
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime

from ..common import load_config, config, ModelFactory
from ..protocol import AgentTeam, Agent, Task as AgentTask
from ..tools.tool_manager import ToolManager
# Remove circular import - we'll pass websocket_manager as parameter
from ..common.models import (
    AgentDecisionMessage, AgentThinkingMessage, ToolDecisionMessage,
    ToolExecuteMessage, AgentResultMessage, TaskResultMessage
)


class AgentExecutor:
    """Agent executor that integrates with AgentMesh core logic"""

    def __init__(self, websocket_manager=None):
        self.model_factory = ModelFactory()
        self.tool_manager = ToolManager()
        self.teams_cache = {}
        self.websocket_manager = websocket_manager

        # Load configuration and tools
        load_config()
        self.tool_manager.load_tools("agentmesh/tools")

    def create_team_from_config(self, team_name: str) -> Optional[AgentTeam]:
        """Create a team from configuration"""
        # Check cache first
        if team_name in self.teams_cache:
            return self.teams_cache[team_name]

        # Get teams configuration
        teams_config = config().get("teams", {})

        # Check if the specified team exists
        if team_name not in teams_config:
            print(f"Error: Team '{team_name}' not found in configuration.")
            return None

        # Get team configuration
        team_config = teams_config[team_name]

        # Get team's model
        team_model_name = team_config.get("model", "gpt-4o")
        team_model = self.model_factory.get_model(team_model_name)

        # Get team's max_steps
        team_max_steps = team_config.get("max_steps", 20)

        # Create team with the model
        team = AgentTeam(
            name=team_name,
            description=team_config.get("description", ""),
            rule=team_config.get("rule", ""),
            model=team_model,
            max_steps=team_max_steps
        )

        # Create and add agents to the team
        agents_config = team_config.get("agents", [])
        for agent_config in agents_config:
            # Check if agent has a specific model
            if agent_config.get("model"):
                agent_model = self.model_factory.get_model(agent_config.get("model"))
            else:
                agent_model = team_model

            # Get agent's max_steps
            agent_max_steps = agent_config.get("max_steps")

            agent = Agent(
                name=agent_config.get("name", ""),
                system_prompt=agent_config.get("system_prompt", ""),
                model=agent_model,
                description=agent_config.get("description", ""),
                max_steps=agent_max_steps
            )

            # Add tools to the agent if specified
            tool_names = agent_config.get("tools", [])
            for tool_name in tool_names:
                tool = self.tool_manager.create_tool(tool_name)
                if tool:
                    agent.add_tool(tool)
                else:
                    print(f"Warning: Tool '{tool_name}' not found for agent '{agent.name}'")

            # Add agent to team
            team.add(agent)

        # Cache the team
        self.teams_cache[team_name] = team
        return team

    def execute_task_with_team_streaming(self, task_id: str, task_content: str, team_name: str = "general_team"):
        """Execute a task using AgentMesh team with real streaming"""
        try:
            # Create team
            team = self.create_team_from_config(team_name)
            if not team:
                self._send_task_result(task_id, "failed")
                return

            # Create task
            agent_task = AgentTask(content=task_content)

            # Execute task with real streaming using run_async
            # Remove signal-based timeout to avoid interfering with Ctrl+C
            self._execute_task_with_run_async_streaming(team, agent_task, task_id)

        except Exception as e:
            print(f"Error executing task {task_id}: {e}")
            self._send_task_result(task_id, "failed")

    def _execute_task_with_run_async_streaming(self, team: AgentTeam, task: AgentTask, task_id: str):
        """Execute task using run_async for real streaming"""
        try:
            print(f"Starting streaming execution for task {task_id}")

            # For now, let's use the simpler synchronous approach to avoid issues
            print("Using synchronous execution for safety")
            result = team.run_async(task, output_mode="logger")
            for agent_result in result:
                self._send_agent_decision(task_id, agent_result.get('agent_id'), agent_result.get('agent_name'),
                                          agent_result.get('subtask'))
                res_text = f"🤖 {agent_result.get('agent_name')}\n\n{agent_result.get('final_answer')}"
                print(res_text)
                for action in agent_result.get("actions"):
                    tool_result = action.get("tool_result")
                    self._send_tool_decision(task_id, agent_result.get("agent_name"),
                                             tool_name=tool_result.get("tool_name"),
                                             thought=action.get("thought"),
                                             parameters=tool_result.get("input_params"))

                    self._send_tool_execute(task_id, agent_result.get("agent_name"),
                                            tool_name=tool_result.get("tool_name"),
                                            tool_result=tool_result.get("output"), execution_time=0,
                                            status=tool_result.get("status"))

                # Send a simple success message
                self._send_agent_result(task_id, agent_result.get('agent_name'), agent_result.get('final_answer'))
            self._send_task_result(task_id, "success")

            print(f"Task execution completed")

        except Exception as e:
            print(f"Error in streaming execution: {e}")
            import traceback
            traceback.print_exc()
            self._send_task_result(task_id, "failed")

    def _send_agent_decision(self, task_id: str, agent_id: str, agent_name: str, sub_task: str):
        """Send agent decision message"""
        if not self.websocket_manager:
            return

        message = AgentDecisionMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "agent_id": agent_id,
                "agent_name": agent_name,
                "agent_avatar": "",
                "sub_task": sub_task
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)

    def _send_task_result(self, task_id: str, status: str):
        """Send task completion message"""
        if not self.websocket_manager:
            return

        message = TaskResultMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "status": status
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)

    def _send_agent_thinking(self, task_id: str, agent_name: str, thought: str):
        """Send agent thinking message"""
        if not self.websocket_manager:
            return

        from ..common.models import AgentThinkingMessage

        message = AgentThinkingMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "agent_id": agent_name,
                "thought": thought
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)

    def _send_agent_result(self, task_id: str, agent_name: str, result: str):
        """Send agent result message"""
        if not self.websocket_manager:
            return

        from ..common.models import AgentResultMessage

        message = AgentResultMessage(
            task_id=task_id,
            data={
                "agent_id": agent_name,
                "result": result
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)

    def _send_tool_decision(self, task_id: str, agent_name: str, tool_name: str, thought: str, parameters: dict):
        """Send tool decision message"""
        if not self.websocket_manager:
            return

        from ..common.models import ToolDecisionMessage

        message = ToolDecisionMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "agent_id": agent_name,
                "tool_id": tool_name,
                "tool_name": tool_name,
                "thought": thought,
                "parameters": parameters
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)

    def _send_tool_execute(self, task_id: str, agent_name: str, tool_name: str, status: str,
                           execution_time: int, tool_result):
        """Send tool execution message"""
        if not self.websocket_manager:
            return

        from ..common.models import ToolExecuteMessage

        message = ToolExecuteMessage(
            task_id=task_id,
            data={
                "task_id": task_id,
                "agent_id": agent_name,
                "tool_name": tool_name,
                "status": status,
                "execution_time": execution_time,
                "tool_result": tool_result
            }
        )
        self.websocket_manager.broadcast_to_task(task_id, message)


# Global agent executor instance - will be initialized with websocket_manager later
agent_executor = None
