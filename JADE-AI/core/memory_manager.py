#!/usr/bin/env python3
"""
JADE Memory Manager
Handles conversational memory: people, context, conversation history
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import centralized paths
try:
    from .paths import GP_MEMORY_PATH
except ImportError:
    from paths import GP_MEMORY_PATH


class MemoryManager:
    """
    Manage JADE's conversational memory

    Capabilities:
    - Remember people ("this is my mentor Constant")
    - Track conversation history
    - Maintain session context
    - Persist memory across sessions
    """

    def __init__(self):
        # Use centralized path config (deployable via GP_MEMORY_PATH env var)
        self.memory_path = GP_MEMORY_PATH
        self.people_file = self.memory_path / "people.json"
        self.context_file = self.memory_path / "context.json"
        self.conversations_file = self.memory_path / "conversations.jsonl"

        # Ensure directory and files exist
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self._ensure_files_exist()

        # Load memory
        self.people_data = self._load_people()
        self.context = self._load_context()

    def _ensure_files_exist(self):
        """Create memory files if they don't exist"""
        if not self.people_file.exists():
            initial_people = {
                "people": [],
                "owner": {
                    "name": "Jimmie",
                    "role": "Owner",
                    "relationship": "My creator and operator",
                    "met_date": datetime.now().isoformat(),
                    "context": "Primary user, cloud security engineer"
                },
                "last_updated": datetime.now().isoformat()
            }
            with open(self.people_file, 'w') as f:
                json.dump(initial_people, f, indent=2)

        if not self.context_file.exists():
            initial_context = {
                "current_user": "Jimmie",
                "active_project": None,
                "last_scan": None,
                "conversation_topic": None,
                "session_start": None,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.context_file, 'w') as f:
                json.dump(initial_context, f, indent=2)

        if not self.conversations_file.exists():
            self.conversations_file.touch()

    def _load_people(self) -> Dict:
        """Load people database"""
        with open(self.people_file) as f:
            return json.load(f)

    def _load_context(self) -> Dict:
        """Load current context"""
        with open(self.context_file) as f:
            return json.load(f)

    def _save_people(self):
        """Save people database"""
        self.people_data["last_updated"] = datetime.now().isoformat()
        with open(self.people_file, 'w') as f:
            json.dump(self.people_data, f, indent=2)

    def _save_context(self):
        """Save current context"""
        self.context["last_updated"] = datetime.now().isoformat()
        with open(self.context_file, 'w') as f:
            json.dump(self.context, f, indent=2)

    # People Management

    def remember_person(self, name: str, role: str = None, relationship: str = None, context: str = None) -> str:
        """
        Remember a new person

        Args:
            name: Person's name
            role: Their role (e.g., "Mentor", "Colleague", "Client")
            relationship: Relationship to Jimmie
            context: Additional context

        Returns:
            Confirmation message
        """
        # Check if already known
        existing = self.get_person(name)
        if existing:
            return f"I already know {name}! They're {existing.get('role', 'someone I know')}."

        # Add new person
        person = {
            "name": name,
            "role": role or "Contact",
            "relationship": relationship or f"Someone Jimmie introduced me to",
            "met_date": datetime.now().isoformat(),
            "interactions": 0,
            "context": context or "",
            "last_seen": datetime.now().isoformat()
        }

        self.people_data["people"].append(person)
        self._save_people()

        return f"Nice to meet you, {name}! I've added you to my memory as {role or 'a contact'}."

    def get_person(self, name: str) -> Optional[Dict]:
        """Get information about a person"""
        name_lower = name.lower()

        # Check owner
        if self.people_data["owner"]["name"].lower() == name_lower:
            return self.people_data["owner"]

        # Check people list
        for person in self.people_data["people"]:
            if person["name"].lower() == name_lower:
                return person

        return None

    def update_person_interaction(self, name: str):
        """Increment interaction count for a person"""
        person = self.get_person(name)
        if person and person != self.people_data["owner"]:
            for p in self.people_data["people"]:
                if p["name"].lower() == name.lower():
                    p["interactions"] = p.get("interactions", 0) + 1
                    p["last_seen"] = datetime.now().isoformat()
                    self._save_people()
                    break

    def list_people(self) -> List[Dict]:
        """Get list of all known people"""
        return [self.people_data["owner"]] + self.people_data["people"]

    # Context Management

    def update_context(self, **kwargs):
        """
        Update session context

        Args:
            current_user: Active user
            active_project: Current project being discussed
            last_scan: Last scan mentioned
            conversation_topic: Current topic
        """
        for key, value in kwargs.items():
            if key in self.context:
                self.context[key] = value

        if "session_start" not in self.context or not self.context["session_start"]:
            self.context["session_start"] = datetime.now().isoformat()

        self._save_context()

    def get_context(self) -> Dict:
        """Get current session context"""
        return self.context.copy()

    # Conversation History

    def log_conversation(self, user: str, query: str, response: str, context_type: str = None, metadata: Dict = None):
        """
        Log a conversation exchange

        Args:
            user: User who asked
            query: User's question
            response: JADE's response
            context_type: Type of query (audit_query, knowledge_query, introduction, etc.)
            metadata: Additional metadata
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "query": query,
            "response": response[:200] + "..." if len(response) > 200 else response,  # Truncate long responses
            "context": {
                "type": context_type or "unknown",
                "active_project": self.context.get("active_project"),
                "metadata": metadata or {}
            }
        }

        # Append to JSONL
        with open(self.conversations_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        # Update person interaction count if user is known
        self.update_person_interaction(user)

    def get_recent_conversations(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        if not self.conversations_file.exists():
            return []

        conversations = []
        with open(self.conversations_file) as f:
            for line in f:
                if line.strip():
                    conversations.append(json.loads(line))

        # Return most recent
        return conversations[-limit:] if len(conversations) > limit else conversations

    def search_conversations(self, keyword: str, limit: int = 5) -> List[Dict]:
        """Search conversation history by keyword"""
        if not self.conversations_file.exists():
            return []

        matches = []
        with open(self.conversations_file) as f:
            for line in f:
                if line.strip() and keyword.lower() in line.lower():
                    try:
                        matches.append(json.loads(line))
                    except:
                        pass

        return matches[-limit:] if len(matches) > limit else matches

    # Intent Detection for Introductions

    def is_introduction(self, query: str) -> Optional[Dict]:
        """
        Detect if query is introducing someone

        Returns:
            Dict with name and role if introduction detected, None otherwise
        """
        query_lower = query.lower()

        introduction_patterns = [
            "this is my",
            "meet my",
            "i'd like you to meet",
            "let me introduce",
            "this is",
            "meet"
        ]

        is_intro = any(pattern in query_lower for pattern in introduction_patterns)
        if not is_intro:
            return None

        # Extract name and role
        # Common patterns:
        # - "this is my mentor Constant"
        # - "meet my colleague John"
        # - "this is Sarah, she's my manager"

        result = {"name": None, "role": None}

        # Look for role keywords
        role_keywords = {
            "mentor": "Mentor",
            "colleague": "Colleague",
            "manager": "Manager",
            "friend": "Friend",
            "client": "Client",
            "partner": "Partner",
            "boss": "Boss",
            "team member": "Team Member",
            "coworker": "Coworker"
        }

        for keyword, role in role_keywords.items():
            if keyword in query_lower:
                result["role"] = role
                # Try to extract name after role
                idx = query_lower.find(keyword)
                after_role = query[idx + len(keyword):].strip()
                # Name is usually the next word
                name_parts = after_role.split()
                if name_parts:
                    result["name"] = name_parts[0].strip(',."\'')
                break

        # If no role found, try "this is NAME"
        if not result["name"]:
            if "this is " in query_lower:
                idx = query_lower.find("this is ")
                after_this_is = query[idx + 8:].strip()
                name_parts = after_this_is.split()
                if name_parts:
                    result["name"] = name_parts[0].strip(',."\'')

        return result if result["name"] else None

    def handle_introduction(self, query: str) -> str:
        """
        Handle introduction and remember person

        Returns:
            Greeting message
        """
        intro_info = self.is_introduction(query)
        if not intro_info:
            return None

        name = intro_info["name"]
        role = intro_info["role"]

        # Remember the person
        greeting = self.remember_person(
            name=name,
            role=role,
            relationship=f"Jimmie's {role.lower()}" if role else "Someone Jimmie knows"
        )

        # Generate friendly response
        if role:
            response = f"Nice to meet you, {name}! I'm JADE, Jimmie's cloud security AI assistant. "
            response += f"I help with security scanning, auto-fixing vulnerabilities, and keeping track of our projects. "
            response += f"As Jimmie's {role.lower()}, feel free to ask me about any of our work!\n\n"
        else:
            response = f"Nice to meet you, {name}! I'm JADE, Jimmie's cloud security AI. "
            response += f"I'm here to help with security work. Feel free to ask me anything!\n\n"

        response += "Try asking:\n"
        response += "- 'tell me about our latest scan'\n"
        response += "- 'what projects do we have?'\n"
        response += "- 'how is FINANCE-project doing?'"

        return response

    # Statistics

    def get_stats(self) -> Dict:
        """Get memory statistics"""
        conversations_count = 0
        if self.conversations_file.exists():
            with open(self.conversations_file) as f:
                conversations_count = sum(1 for line in f if line.strip())

        return {
            "people_known": len(self.people_data["people"]) + 1,  # +1 for owner
            "conversations_logged": conversations_count,
            "session_active": bool(self.context.get("session_start")),
            "active_project": self.context.get("active_project"),
            "last_updated": self.context.get("last_updated")
        }


# CLI for testing
if __name__ == "__main__":
    import sys

    mm = MemoryManager()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "stats":
            stats = mm.get_stats()
            print("📊 Memory Statistics:")
            for key, value in stats.items():
                print(f"   {key}: {value}")

        elif command == "people":
            people = mm.list_people()
            print(f"👥 Known People ({len(people)}):")
            for person in people:
                print(f"\n   {person['name']} ({person.get('role', 'Unknown role')})")
                print(f"      Relationship: {person.get('relationship', 'N/A')}")
                print(f"      Met: {person.get('met_date', 'Unknown')}")
                if "interactions" in person:
                    print(f"      Interactions: {person['interactions']}")

        elif command == "add" and len(sys.argv) >= 3:
            name = sys.argv[2]
            role = sys.argv[3] if len(sys.argv) > 3 else None
            msg = mm.remember_person(name, role)
            print(msg)

        elif command == "intro" and len(sys.argv) >= 3:
            intro_text = " ".join(sys.argv[2:])
            response = mm.handle_introduction(intro_text)
            print(response if response else "Not an introduction")

        elif command == "recent":
            convos = mm.get_recent_conversations(5)
            print(f"💬 Recent Conversations ({len(convos)}):")
            for conv in convos:
                print(f"\n   [{conv['timestamp']}] {conv['user']}: {conv['query'][:50]}...")
                print(f"      Type: {conv['context']['type']}")

        else:
            print("Usage:")
            print("  python memory_manager.py stats")
            print("  python memory_manager.py people")
            print("  python memory_manager.py add NAME [ROLE]")
            print("  python memory_manager.py intro 'this is my mentor Constant'")
            print("  python memory_manager.py recent")

    else:
        # Demo
        print("=== JADE Memory Manager Demo ===\n")
        print(mm.get_stats())
