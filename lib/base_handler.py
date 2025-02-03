from typing import List, Optional, Any, TypeVar, Generic
from lib.command_builder import CommandBuilder
from lib.op import OpClient

T = TypeVar('T')

class BaseOpHandler:
    """Base class for 1Password CLI handlers with common command execution patterns"""
    
    def __init__(self, resource_type: str):
        """
        Args:
            resource_type: The type of resource (e.g., "user", "group", "item")
        """
        self.resource_type = resource_type
        self.client = OpClient()

    async def _execute(
        self,
        subcommand: str,
        args: Optional[List[str]] = None,
        options: Optional[dict] = None,
    ) -> Any:
        """Execute a command with standard error handling
        
        Args:
            subcommand: The subcommand to execute (e.g., "list", "get")
            args: Optional positional arguments
            options: Optional key-value pairs for command options
        """
        cmd = (
            CommandBuilder(self.resource_type)
            .subcommand(subcommand)
        )
        
        # Add positional args
        if args:
            for arg in args:
                cmd.arg(arg)
                
        # Add options
        if options:
            for key, value in options.items():
                if value is not None:  # Only add options with values
                    cmd.option(key, value)
        
        return await self.client.execute_command(cmd.build()) 