import json
from datetime import datetime
from typing import List, Dict, Any
from models import AgentMemory, MemoryEntry, UserPreference
import os

class Memory:
    def __init__(self, user_preference: UserPreference):
        self.user_preference = user_preference
        self.memory_file = "agent_memory.json"
        self.memory = self._load_memory()
        
    def _load_memory(self) -> AgentMemory:
        """Load memory from JSON file or create new if not exists"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    return AgentMemory(**data)
            except Exception as e:
                print(f"Error loading memory: {e}")
                return AgentMemory()
        return AgentMemory()
    
    def _save_memory(self):
        """Save memory to JSON file"""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory.model_dump(), f, indent=2)
        except Exception as e:
            print(f"Error saving memory: {e}")
    
    def add_entry(self, interaction_type: str, content: Dict[str, Any], importance: int = 5):
        """Add a new memory entry"""
        entry = MemoryEntry(
            timestamp=datetime.utcnow().isoformat(),
            interaction_type=interaction_type,
            content=content,
            importance=importance
        )
        
        self.memory.entries.append(entry)
        
        # Maintain memory size based on user preference
        if len(self.memory.entries) > self.user_preference.memory_retention:
            # Remove oldest entries with lowest importance
            self.memory.entries.sort(key=lambda x: (x.importance, x.timestamp))
            self.memory.entries = self.memory.entries[-self.user_preference.memory_retention:]
        
        self._save_memory()
    
    def get_recent_context(self, n_entries: int = 5) -> List[MemoryEntry]:
        """Get the n most recent memory entries"""
        return sorted(self.memory.entries, key=lambda x: x.timestamp, reverse=True)[:n_entries]
    
    def update_context(self, context: Dict[str, Any]):
        """Update the current context"""
        self.memory.current_context.update(context)
        self._save_memory()
    
    def get_context(self) -> Dict[str, Any]:
        """Get the current context"""
        return self.memory.current_context
    
    def clear_memory(self):
        """Clear all memory entries"""
        self.memory = AgentMemory()
        self._save_memory()

    def save_memory(self):
        """Save memory to a file"""
        try:
            with open("memory.json", "w") as f:
                json.dump(self.memory.model_dump(), f, indent=2)
            print("✓ Memory saved successfully")
        except Exception as e:
            print(f"✗ Error saving memory: {e}") 