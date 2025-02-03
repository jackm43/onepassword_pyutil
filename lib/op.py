import logging
import asyncio
import json
import subprocess
import os
from typing import List, Optional, Union, Any, Dict
from dataclasses import dataclass

# Define SubprocessError type - only use subprocess.SubprocessError
SubprocessError = subprocess.SubprocessError

logger = logging.getLogger(__name__)

class OpClientError(Exception):
    """Base exception for 1Password CLI errors"""
    pass

class OpVersionError(OpClientError):
    """Raised when 1Password CLI version is incompatible"""
    pass

class OpCommandError(OpClientError):
    """Raised when a 1Password CLI command fails"""
    pass

class AuthenticationError(OpClientError):
    """Raised when authentication is required or fails"""
    pass

@dataclass
class CliVersion:
    """Structured version information"""
    major: int
    minor: int
    patch: int

    @classmethod
    def from_string(cls, version_str: str) -> 'CliVersion':
        """Create version object from string like '2.25.0'"""
        try:
            major, minor, patch = map(int, version_str.strip().split("."))
            return cls(major=major, minor=minor, patch=patch)
        except (ValueError, AttributeError) as e:
            raise OpVersionError(f"Invalid version format: {version_str}") from e

    def meets_minimum(self, min_version: 'CliVersion') -> bool:
        """Check if version meets minimum requirements"""
        return (self.major, self.minor, self.patch) >= (
            min_version.major, min_version.minor, min_version.patch
        )

class OpClient:
    """Client for interacting with the 1Password CLI"""
    
    MIN_VERSION = CliVersion(2, 25, 0)

    def __init__(self, account: Optional[str] = None, service_account_token: Optional[str] = None):
        self.account = account
        self.service_account_token = service_account_token
        self._verify_cli_version()

    def _verify_cli_version(self) -> None:
        """Verify the installed op CLI meets minimum version requirements"""
        try:
            result = subprocess.run(['op', '--version'], capture_output=True, text=True)
            version = CliVersion.from_string(result.stdout)
            if not version.meets_minimum(self.MIN_VERSION):
                raise OpVersionError(
                    f"1Password CLI version {version} is below minimum required {self.MIN_VERSION}"
                )
        except FileNotFoundError as e:
            raise OpClientError("1Password CLI not found. Please install it first.") from e

    async def execute_command(
        self, 
        command: List[str], 
        input_data: Optional[Union[str, bytes]] = None,
        decode_json: bool = True
    ) -> Any:
        """Execute a 1Password CLI command asynchronously
        
        Args:
            command: List of command arguments
            input_data: Optional input data for the command
            decode_json: Whether to decode the output as JSON
            
        Returns:
            Command output (decoded from JSON if decode_json=True)
            
        Raises:
            OpCommandError: If the command fails
            AuthenticationError: If authentication is required
        """
        env = os.environ.copy()
        if self.service_account_token:
            env["OP_SERVICE_ACCOUNT_TOKEN"] = self.service_account_token

        if self.account:
            command.extend(['--account', self.account])

        try:
            logger.debug(f"Executing op command: {' '.join(command)}")
            process = await asyncio.create_subprocess_exec(
                'op',
                *command,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            stdout, stderr = await process.communicate(
                input_data.encode() if isinstance(input_data, str) else input_data
            )

            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                # Check for various forms of authentication errors. had a few bugs with this lole
                auth_error_messages = [
                    "not currently signed in",
                    "account is not signed in",
                    "not signed in",
                ]
                
                if any(msg in error_msg.lower() for msg in auth_error_messages):
                    raise AuthenticationError(
                        "Please authenticate with 1Password CLI first using 'op signin'"
                    )

                # Extract just the error message without the help text
                error_lines = error_msg.split('\n')
                error_msg = next(
                    (line for line in error_lines if line.startswith('[ERROR]')),
                    error_lines[0] if error_lines else "Unknown error"
                )
                logger.debug(f"Full CLI error: {stderr.decode()}")
                logger.error(f"Command failed: {error_msg}")
                raise OpCommandError(f"Command failed: {error_msg}")

            output = stdout.decode().strip()
            
            if not output:
                return None
                
            if decode_json:
                try:
                    return json.loads(output)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON output: {output}")
                    raise OpCommandError("Failed to decode command output as JSON") from e
            
            return output

        except (OSError, SubprocessError) as e:
            logger.error(f"Failed to execute command: {e}")
            raise OpCommandError(f"Failed to execute command: {e}") from e

    def execute_command_sync(
        self,
        command: List[str],
        input_data: Optional[Union[str, bytes]] = None,
        decode_json: bool = True
    ) -> Any:
        """Synchronous version of execute_command"""
        return asyncio.run(self.execute_command(command, input_data, decode_json))

    async def run_command_async(self, cmd: str) -> Union[Dict[str, Any], list]:
        """Run a 1Password CLI command asynchronously
        
        Args:
            cmd: Command string to execute
            
        Returns:
            Parsed JSON response from command
            
        Raises:
            AuthenticationError: If authentication is required
            OpCommandError: If command execution fails
        """
        # Split command string and add base command
        full_cmd = cmd.split()
        full_cmd.extend(["--format=json"])
        
        return await self.execute_command(full_cmd, decode_json=True)

    def run_command(self, cmd: str) -> Any:
        """Run a command synchronously"""
        try:
            # Use asyncio.get_event_loop() instead of asyncio.run()
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.run_command_async(cmd))
        except Exception as e:
            logger.error(f"Command failed: {str(e)}")
            raise

    async def run_multiple_commands(self, commands: List[str]) -> List[str]:
        """
        Run multiple commands concurrently and return the JSON responses.
        Use this when you want to.. well, run multiple commands at once, side-by-side.
        """
        tasks = [self.run_command_async(cmd) for cmd in commands]
        return await asyncio.gather(*tasks)

    async def execute_with_rate_limit(
        self,
        command: List[str],
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> Any:
        """Execute a command with rate limit handling
        
        Args:
            command: Command to execute
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds before retry
            
        Returns:
            Command result
            
        Raises:
            OpCommandError: If all retries fail
        """
        for attempt in range(max_retries + 1):
            try:
                return await self.execute_command(command)
            except OpCommandError as e:
                if "rate limit exceeded" in str(e).lower():
                    if attempt == max_retries:
                        logger.error("Rate limit retries exhausted")
                        raise
                        
                    delay = initial_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Rate limit hit, retrying in {delay:.1f}s")
                    await asyncio.sleep(delay)
                    continue
                raise
