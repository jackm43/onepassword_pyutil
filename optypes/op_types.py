from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, root_validator, Field


@dataclass
class OpCommand:
    OP: str = "op"

@dataclass
class BaseCmds:
    ACCOUNT: str = "account"
    CONNECT: str = "connect"
    DOCUMENT: str = "document"
    EVENTS_API: str = "events-api"
    GROUP: str = "group"
    ITEM: str = "item"
    PLUGIN: str = "plugin"
    SERVICE_ACCOUNT: str = "service-account"
    USER: str = "user"
    VAULT: str = "vault"

@dataclass
class CommandNode:
    name: str
    handler: Optional[Callable] = None
    sub_commands: Dict[str, 'CommandNode'] = field(default_factory=dict)

    def add_subcommand(self, subcommand: 'CommandNode'):
        self.sub_commands[subcommand.name.lower()] = subcommand

    def get_subcommand(self, name: str) -> Optional['CommandNode']:
        return self.sub_commands.get(name.lower())

@dataclass
class Command:
    name: str
    sub_commands: dict = field(default_factory=dict)

    def __getattr__(self, item):
        if item in self.sub_commands:
            return self.sub_commands[item]
        raise AttributeError(f"No such subcommand: '{item}' in command '{self.name}'.")

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Command(name='{self.name}')"

class SingletonMeta(type):
# https://github.com/AmirLavasani/python-design-patterns/blob/main/singleton/singleton_metaclass.py

    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
    
@dataclass
class Commands(metaclass=SingletonMeta):
    root: CommandNode = field(default_factory=lambda: CommandNode(name="root"))

    def register_command_path(self, command_path: List[str], handler: Callable) -> None:
        current_node = self.root
        for cmd in command_path:
            cmd_lower = cmd.lower()
            next_node = current_node.get_subcommand(cmd_lower)
            if next_node is None:
                next_node = CommandNode(name=cmd)
                current_node.add_subcommand(next_node)
            current_node = next_node
        current_node.handler = handler

    def list_commands(self, current_node: Optional[CommandNode] = None, prefix: str = "") -> List[str]:
        if current_node is None:
            current_node = self.root
        commands = []
        for cmd, node in current_node.sub_commands.items():
            full_cmd = f"{prefix} {node.name}".strip()
            commands.append(full_cmd)
            commands.extend(self.list_commands(node, full_cmd))
        return commands

    def __str__(self) -> str:
        return "Commands Singleton"

    def __repr__(self) -> str:
        return "Commands()"

    def handle_unknown(self) -> str:
        print("Unknown command. No action taken.")
        return "Unknown command."
@dataclass
class VaultCommand:
    commands: Commands = field(default_factory=Commands)
    BASE_COMMAND: Command = field(init=False)
    COMMANDS: dict = field(init=False)

    def __post_init__(self):
        self.BASE_COMMAND = self.commands.VAULT
        self.COMMANDS = self.BASE_COMMAND.sub_commands

@dataclass
class Permissions():
    ALLOW_VIEWING: str = "allow_viewing"
    MANAGE_VAULT: str = "manage_vault"
    ALLOW_EDITING: str = "allow_editing"
    VIEW_ITEMS: str = "view_items"
    CREATE_ITEMS: str = "create_items"
    EDIT_ITEMS: str = "edit_items"
    ARCHIVE_ITEMS: str = "archive_items"
    DELETE_ITEMS: str = "delete_items"
    VIEW_AND_COPY_PASSWORDS: str = "view_and_copy_passwords"
    VIEW_ITEM_HISTORY: str = "view_item_history"
    IMPORT_ITEMS: str = "import_items"
    EXPORT_ITEMS: str = "export_items"
    COPY_AND_SHARE_ITEMS: str = "copy_and_share_items"
    PRINT_ITEMS: str = "print_items"

class PermissionOperator(Enum):
    GRANT = "grant"
    REVOKE = "revoke"


class TestingItems():
    TEST_VAULT_ID: str = "u4ootfqult5kep6xlrs4sil7za"
    TEST_VAULT_ID: str = "4lgmhntcrfyquabprztyp5zwi4"
    TEST_ITEM_ID: str = "wnnu6xbaaobllm4by4ws7choii"
    TEST_TEST_ITEM_ID: str = "ati7vxbc5honwxn4edvj4b7hya"
    SEARCH_TERM: str = "huge"

class GroupSet():
    OWNERS: str = "Owners"


class VaultPermissionUpdate(BaseModel):
    group_id: str
    permissions: str
    vault_id: str
    vault_name: str

class VaultUserPermissionUpdate(BaseModel):
    vault_id: str
    vault_name: str
    user_id: str
    user_email: str
    permissions: str

class UserDetails(BaseModel):
    """User details model with optional permissions field"""
    id: str
    name: str
    email: str
    type: str
    state: str
    created_at: str
    updated_at: str
    last_auth_at: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)  # Make permissions optional with empty default

class UserOverview(BaseModel):
    id: str
    name: str
    email: str
    type: str
    state: str    

class Item(BaseModel):
    id: str
    title: str
    version: int
    vault: VaultOverview
    category: str
    last_edited_by: str
    created_at: str
    updated_at: str
    additional_information: Optional[str] = None
    urls: Optional[List[Dict]] = [{}]
    sections: Optional[List[Dict]] = []
    fields: List[ItemField]


    @root_validator(pre=True)
    def process_fields_and_vault_id(cls, values):
        fields = values.get('fields', [])
        filtered_fields = []
        for field in fields:
            if isinstance(field, dict) and field.get('type') != 'CONCEALED':
                filtered_fields.append(field)
            elif isinstance(field, ItemField) and field.type != 'CONCEALED':
                filtered_fields.append(field)
        values['fields'] = filtered_fields
        return values


@dataclass
class ItemField:
    id: Optional[str] = None
    type: Optional[str] = None
    purpose: Optional[str] = None
    label: Optional[str] = None
    value: Optional[str] = None
    reference: Optional[str] = None
    password_details: Optional[Dict] = None

    def dict(self, exclude_none: bool = False) -> Dict[str, Any]:
        """Convert to dictionary, optionally excluding None values"""
        d = {
            'id': self.id,
            'type': self.type,
            'purpose': self.purpose,
            'label': self.label,
            'value': self.value,
            'reference': self.reference,
            'password_details': self.password_details
        }
        if exclude_none:
            return {k: v for k, v in d.items() if v is not None}
        return d

    def get(self, key: str, default: Any = None) -> Any:
        """Mimic dict.get() behavior for compatibility"""
        return getattr(self, key, default)


class VaultOverview(BaseModel):
    id: str
    name: str
    version: Optional[int] = None


class VaultDetails(BaseModel):
    id: str
    name: str
    content_version: int
    attribute_version: int
    items: int
    type: str
    created_at: str
    updated_at: str

from lib.op import OpClient
class BaseHandler:
    def __init__(self):
        """
        Initializes the handler and registers its decorated command methods.
        """
        self.register_commands()
        self.client = OpClient()

    def register_commands(self):
        """
        Registers all methods decorated with @command as commands in the Commands singleton.
        """
        commands_singleton = Commands()
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if hasattr(method, '_command_path'):
                path = method._command_path
                arguments = method._args
                options = method._options
                # Create a CommandNode with arguments and options
                current_node = commands_singleton.root
                for cmd in path:
                    cmd_lower = cmd.lower()
                    if cmd_lower not in current_node.sub_commands:
                        current_node.sub_commands[cmd_lower] = CommandNode(name=cmd)
                    current_node = current_node.sub_commands[cmd_lower]
                current_node.handler = method
                current_node.arguments = arguments
                current_node.options = options


@dataclass
class ArgumentSpec:
    name: str
    type: type = str
    default: Any = None
    required: bool = True
    help: str = ""


@dataclass
class OptionSpec:
    name: str
    type: type = bool
    default: Any = False
    required: bool = False
    help: str = ""

class GroupOverview(BaseModel):
    """Basic group information returned by group list"""
    id: str
    name: str
    description: Optional[str] = None
    state: Optional[str] = None
    created_at: Optional[str] = None

class GroupDetails(GroupOverview):
    """Detailed group information returned by group get"""
    type: str
    permissions: Optional[Dict[str, Any]] = None
    members: Optional[List[Dict[str, Any]]] = None
    updated_at: str