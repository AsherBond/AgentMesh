"""
Bash tool - Execute bash commands
"""

import os
import subprocess
import tempfile
from typing import Dict, Any

from agentmesh.tools.base_tool import BaseTool, ToolResult
from agentmesh.tools.utils.truncate import truncate_tail, format_size, DEFAULT_MAX_LINES, DEFAULT_MAX_BYTES


class Bash(BaseTool):
    """Tool for executing bash commands"""
    
    name: str = "bash"
    description: str = f"Execute a bash command in the current working directory. Returns stdout and stderr. Output is truncated to last {DEFAULT_MAX_LINES} lines or {DEFAULT_MAX_BYTES // 1024}KB (whichever is hit first). If truncated, full output is saved to a temp file."
    
    params: dict = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Bash command to execute"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (optional, default: 30)"
            }
        },
        "required": ["command"]
    }
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.cwd = self.config.get("cwd", os.getcwd())
        self.default_timeout = self.config.get("timeout", 30)
        # Dangerous commands that should be blocked
        self.command_ban_set = {
            "halt", "poweroff", "shutdown", "reboot", "rm", "kill",
            "exit", "sudo", "su", "userdel", "groupdel", "logout", "alias"
        }
    
    def execute(self, args: Dict[str, Any]) -> ToolResult:
        """
        Execute a bash command
        
        :param args: Dictionary containing the command and optional timeout
        :return: Command output or error
        """
        command = args.get("command", "").strip()
        timeout = args.get("timeout", self.default_timeout)
        
        if not command:
            return ToolResult.fail("Error: command parameter is required")
        
        # Check if command is safe
        if not self._is_safe_command(command):
            return ToolResult.fail(f"Error: Command '{command}' is not allowed for security reasons")
        
        try:
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout
            )
            
            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            
            # Check if we need to save full output to temp file
            temp_file_path = None
            total_bytes = len(output.encode('utf-8'))
            
            if total_bytes > DEFAULT_MAX_BYTES:
                # Save full output to temp file
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log', prefix='bash-') as f:
                    f.write(output)
                    temp_file_path = f.name
            
            # Apply tail truncation
            truncation = truncate_tail(output)
            output_text = truncation.content or "(no output)"
            
            # Build result
            details = {}
            
            if truncation.truncated:
                details["truncation"] = truncation.to_dict()
                if temp_file_path:
                    details["full_output_path"] = temp_file_path
                
                # Build notice
                start_line = truncation.total_lines - truncation.output_lines + 1
                end_line = truncation.total_lines
                
                if truncation.last_line_partial:
                    # Edge case: last line alone > 30KB
                    last_line = output.split('\n')[-1] if output else ""
                    last_line_size = format_size(len(last_line.encode('utf-8')))
                    output_text += f"\n\n[Showing last {format_size(truncation.output_bytes)} of line {end_line} (line is {last_line_size}). Full output: {temp_file_path}]"
                elif truncation.truncated_by == "lines":
                    output_text += f"\n\n[Showing lines {start_line}-{end_line} of {truncation.total_lines}. Full output: {temp_file_path}]"
                else:
                    output_text += f"\n\n[Showing lines {start_line}-{end_line} of {truncation.total_lines} ({format_size(DEFAULT_MAX_BYTES)} limit). Full output: {temp_file_path}]"
            
            # Check exit code
            if result.returncode != 0:
                output_text += f"\n\nCommand exited with code {result.returncode}"
                return ToolResult.fail({
                    "output": output_text,
                    "exit_code": result.returncode,
                    "details": details if details else None
                })
            
            return ToolResult.success({
                "output": output_text,
                "exit_code": result.returncode,
                "details": details if details else None
            })
            
        except subprocess.TimeoutExpired:
            return ToolResult.fail(f"Error: Command timed out after {timeout} seconds")
        except Exception as e:
            return ToolResult.fail(f"Error executing command: {str(e)}")
    
    def _is_safe_command(self, command: str) -> bool:
        """
        Check if a command is safe to execute
        
        :param command: Command to check
        :return: True if safe, False otherwise
        """
        cmd_parts = command.split()
        if not cmd_parts:
            return False
        
        base_cmd = cmd_parts[0].lower()
        
        # Check ban list
        if base_cmd in self.command_ban_set:
            return False
        
        # Check for sudo/su
        if any(banned in command.lower() for banned in ["sudo ", "su -"]):
            return False
        
        # Check for dangerous rm patterns
        if "rm" in base_cmd and any(flag in command for flag in ["-rf", "-r", "-f"]):
            return False
        
        return True
