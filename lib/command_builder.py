from dataclasses import dataclass
from typing import List, Optional, Union, Any

@dataclass
class CommandBuilder:
    """Builder for 1Password CLI commands"""
    
    def __init__(self, base_command: str):
        self._command: List[str] = [base_command]
        self._format: str = "json"
        self._account: Optional[str] = None
    
    def subcommand(self, cmd: str) -> 'CommandBuilder':
        """Add a subcommand"""
        self._command.append(cmd)
        return self
    
    def arg(self, value: Union[str, int]) -> 'CommandBuilder':
        """Add a positional argument"""
        self._command.append(str(value))
        return self
    
    def option(self, name: str, value: Optional[Any] = None) -> 'CommandBuilder':
        """Add an option with optional value"""
        option_name = f"--{name}" if len(name) > 1 else f"-{name}"
        self._command.append(option_name)
        if value is not None:
            self._command.append(str(value))
        return self
    
    def format(self, fmt: str = "json") -> 'CommandBuilder':
        """Set output format"""
        self._format = fmt
        return self
    
    def account(self, account_id: str) -> 'CommandBuilder':
        """Set account ID"""
        self._account = account_id
        return self
    
    def build(self) -> List[str]:
        """Build the final command list"""
        cmd = self._command.copy()
        
        if self._format:
            cmd.extend(["--format", self._format])
            
        if self._account:
            cmd.extend(["--account", self._account])
            
        return cmd
