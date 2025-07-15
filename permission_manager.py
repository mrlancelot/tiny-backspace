#!/usr/bin/env python3
"""
Permission Manager for Daytona Operations
Handles permission requests and confirmations for sandbox operations
"""

import json
import os
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text


class OperationType(Enum):
    CREATE_SANDBOX = "create_sandbox"
    DELETE_SANDBOX = "delete_sandbox"
    EXECUTE_COMMAND = "execute_command"
    MODIFY_FILES = "modify_files"
    INSTALL_SOFTWARE = "install_software"
    ACCESS_CREDENTIALS = "access_credentials"
    NETWORK_ACCESS = "network_access"


class PermissionLevel(Enum):
    ALWAYS_ALLOW = "always_allow"
    ALWAYS_ASK = "always_ask"
    REMEMBER_CHOICE = "remember_choice"
    DENY = "deny"


@dataclass
class PermissionRequest:
    operation: OperationType
    resource: str
    details: Dict[str, Any]
    timestamp: float
    risk_level: str  # low, medium, high
    

@dataclass
class PermissionDecision:
    request: PermissionRequest
    allowed: bool
    reason: Optional[str]
    remember: bool
    timestamp: float


class PermissionManager:
    def __init__(self, 
                 console: Optional[Console] = None,
                 config_file: str = "~/.daytona/permissions.json",
                 audit_file: str = "~/.daytona/audit.log"):
        """Initialize permission manager"""
        self.console = console or Console()
        self.config_file = Path(config_file).expanduser()
        self.audit_file = Path(audit_file).expanduser()
        
        # Create directories if they don't exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Load saved permissions
        self.saved_permissions = self._load_permissions()
        self.session_permissions = {}  # Temporary session permissions
        
    def _load_permissions(self) -> Dict[str, Dict]:
        """Load saved permission preferences"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.console.print(f"[yellow]Warning: Could not load permissions: {e}")
        return {}
    
    def _save_permissions(self):
        """Save permission preferences"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.saved_permissions, f, indent=2)
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not save permissions: {e}")
    
    def _log_decision(self, decision: PermissionDecision):
        """Log permission decision to audit file"""
        try:
            with open(self.audit_file, 'a') as f:
                log_entry = {
                    "timestamp": datetime.fromtimestamp(decision.timestamp).isoformat(),
                    "operation": decision.request.operation.value,
                    "resource": decision.request.resource,
                    "allowed": decision.allowed,
                    "reason": decision.reason,
                    "details": decision.request.details
                }
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            self.console.print(f"[yellow]Warning: Could not log decision: {e}")
    
    def _get_permission_key(self, request: PermissionRequest) -> str:
        """Generate a unique key for permission caching"""
        return f"{request.operation.value}:{request.resource}"
    
    def _check_saved_permission(self, request: PermissionRequest) -> Optional[bool]:
        """Check if we have a saved permission for this request"""
        key = self._get_permission_key(request)
        
        # Check session permissions first
        if key in self.session_permissions:
            return self.session_permissions[key]
        
        # Check saved permissions
        if key in self.saved_permissions:
            saved = self.saved_permissions[key]
            if saved['level'] == PermissionLevel.ALWAYS_ALLOW.value:
                return True
            elif saved['level'] == PermissionLevel.DENY.value:
                return False
        
        return None
    
    def request_permission(self, 
                         operation: OperationType,
                         resource: str,
                         details: Optional[Dict[str, Any]] = None,
                         risk_level: str = "medium") -> bool:
        """Request permission for an operation"""
        # Create permission request
        request = PermissionRequest(
            operation=operation,
            resource=resource,
            details=details or {},
            timestamp=time.time(),
            risk_level=risk_level
        )
        
        # Check saved permissions
        saved_decision = self._check_saved_permission(request)
        if saved_decision is not None:
            # Log the automatic decision
            decision = PermissionDecision(
                request=request,
                allowed=saved_decision,
                reason="Saved preference",
                remember=False,
                timestamp=time.time()
            )
            self._log_decision(decision)
            return saved_decision
        
        # Show permission request dialog
        allowed, remember = self._show_permission_dialog(request)
        
        # Create decision
        decision = PermissionDecision(
            request=request,
            allowed=allowed,
            reason="User decision",
            remember=remember,
            timestamp=time.time()
        )
        
        # Save decision if requested
        if remember:
            key = self._get_permission_key(request)
            level = PermissionLevel.ALWAYS_ALLOW if allowed else PermissionLevel.DENY
            self.saved_permissions[key] = {
                'level': level.value,
                'timestamp': decision.timestamp
            }
            self._save_permissions()
        else:
            # Save for this session only
            key = self._get_permission_key(request)
            self.session_permissions[key] = allowed
        
        # Log decision
        self._log_decision(decision)
        
        return allowed
    
    def _show_permission_dialog(self, request: PermissionRequest) -> tuple[bool, bool]:
        """Show interactive permission dialog"""
        # Create permission panel
        panel_content = self._create_permission_panel(request)
        
        self.console.print(panel_content)
        
        # Ask for permission
        allowed = Confirm.ask(
            f"Allow this {request.risk_level}-risk operation?",
            default=request.risk_level == "low"
        )
        
        remember = False
        if allowed:
            remember = Confirm.ask(
                "Remember this choice for future requests?",
                default=False
            )
        
        return allowed, remember
    
    def _create_permission_panel(self, request: PermissionRequest) -> Panel:
        """Create a rich panel for permission request"""
        # Determine panel style based on risk
        risk_styles = {
            "low": "green",
            "medium": "yellow", 
            "high": "red"
        }
        style = risk_styles.get(request.risk_level, "yellow")
        
        # Create details table
        table = Table(show_header=False, box=None)
        table.add_column("Field", style="bold")
        table.add_column("Value")
        
        # Add operation details
        table.add_row("Operation:", request.operation.value.replace('_', ' ').title())
        table.add_row("Resource:", request.resource)
        table.add_row("Risk Level:", Text(request.risk_level.upper(), style=style))
        
        # Add additional details
        for key, value in request.details.items():
            table.add_row(f"{key.title()}:", str(value))
        
        # Create description based on operation
        descriptions = {
            OperationType.CREATE_SANDBOX: "This will create a new cloud development environment",
            OperationType.DELETE_SANDBOX: "This will permanently delete the sandbox and all its data",
            OperationType.EXECUTE_COMMAND: "This will run a command inside the sandbox",
            OperationType.MODIFY_FILES: "This will modify files in the sandbox",
            OperationType.INSTALL_SOFTWARE: "This will install new software in the sandbox",
            OperationType.ACCESS_CREDENTIALS: "This will access stored credentials",
            OperationType.NETWORK_ACCESS: "This will make network requests from the sandbox"
        }
        
        description = descriptions.get(request.operation, "This operation requires your permission")
        
        # Create panel content
        content = Table.grid(padding=1)
        content.add_row(Text(description, style="italic"))
        content.add_row("")
        content.add_row(table)
        
        return Panel(
            content,
            title="🔐 Permission Request",
            border_style=style,
            expand=False
        )
    
    def show_permission_summary(self):
        """Show summary of current permissions"""
        if not self.saved_permissions and not self.session_permissions:
            self.console.print("[yellow]No permissions configured yet.")
            return
        
        # Create summary table
        table = Table(title="📋 Permission Summary")
        table.add_column("Operation", style="cyan")
        table.add_column("Resource", style="white")
        table.add_column("Permission", style="green")
        table.add_column("Type", style="yellow")
        
        # Add saved permissions
        for key, value in self.saved_permissions.items():
            operation, resource = key.split(':', 1)
            permission = "✅ Allowed" if value['level'] == PermissionLevel.ALWAYS_ALLOW.value else "❌ Denied"
            table.add_row(operation, resource, permission, "Saved")
        
        # Add session permissions
        for key, allowed in self.session_permissions.items():
            operation, resource = key.split(':', 1)
            permission = "✅ Allowed" if allowed else "❌ Denied"
            table.add_row(operation, resource, permission, "Session")
        
        self.console.print(table)
    
    def reset_permissions(self, scope: str = "all"):
        """Reset permissions"""
        if scope == "all":
            self.saved_permissions = {}
            self.session_permissions = {}
            self._save_permissions()
            self.console.print("[green]✅ All permissions reset")
        elif scope == "session":
            self.session_permissions = {}
            self.console.print("[green]✅ Session permissions reset")
        elif scope == "saved":
            self.saved_permissions = {}
            self._save_permissions()
            self.console.print("[green]✅ Saved permissions reset")
    
    def get_audit_log(self, limit: int = 10) -> List[Dict]:
        """Get recent audit log entries"""
        if not self.audit_file.exists():
            return []
        
        entries = []
        with open(self.audit_file, 'r') as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except:
                    continue
        
        return entries[-limit:]
    
    def show_audit_log(self, limit: int = 10):
        """Display recent audit log entries"""
        entries = self.get_audit_log(limit)
        
        if not entries:
            self.console.print("[yellow]No audit log entries found.")
            return
        
        table = Table(title=f"🔍 Recent Permission Decisions (Last {limit})")
        table.add_column("Time", style="dim")
        table.add_column("Operation", style="cyan")
        table.add_column("Resource", style="white")
        table.add_column("Decision", style="green")
        
        for entry in entries:
            time_str = entry['timestamp'].split('T')[1].split('.')[0]
            decision = "✅ Allowed" if entry['allowed'] else "❌ Denied"
            table.add_row(
                time_str,
                entry['operation'],
                entry['resource'],
                decision
            )
        
        self.console.print(table)


# Context manager for batch permissions
class BatchPermissions:
    """Context manager for batch permission requests"""
    
    def __init__(self, manager: PermissionManager, operation: OperationType):
        self.manager = manager
        self.operation = operation
        self.allowed = False
        
    def __enter__(self):
        # Request permission once for batch operation
        self.allowed = self.manager.request_permission(
            self.operation,
            "Batch Operation",
            {"type": "batch", "description": "Multiple operations will be performed"},
            risk_level="medium"
        )
        return self.allowed
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.allowed:
            self.manager.console.print("[green]✅ Batch operation completed")


# Example usage
if __name__ == "__main__":
    console = Console()
    pm = PermissionManager(console)
    
    # Example permission requests
    print("\n=== Example Permission Requests ===\n")
    
    # Low risk operation
    allowed = pm.request_permission(
        OperationType.EXECUTE_COMMAND,
        "sandbox-123",
        {"command": "ls -la", "purpose": "List files"},
        risk_level="low"
    )
    print(f"Command execution allowed: {allowed}\n")
    
    # High risk operation
    allowed = pm.request_permission(
        OperationType.DELETE_SANDBOX,
        "production-sandbox",
        {"age": "30 days", "size": "50GB"},
        risk_level="high"
    )
    print(f"Sandbox deletion allowed: {allowed}\n")
    
    # Show summary
    pm.show_permission_summary()
    
    # Show audit log
    pm.show_audit_log()