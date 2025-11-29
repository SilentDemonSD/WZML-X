# -*- coding: utf-8 -*-
# User Compressor Session Manager
# Manages video compression settings and user preferences before download

from typing import Dict, List, Optional
from datetime import datetime

class UserCompressionSession:
    """Manages compression session for each user"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.link = None
        self.actions = []  # List of selected compression actions
        self.subtitle_path = None  # Path to uploaded subtitle file
        self.compression_options = {}
        self.created_at = datetime.now()
    
    def set_link(self, link: str):
        """Set the download link"""
        self.link = link
    
    def add_action(self, action: str):
        """Add compression action (e.g., 'compress', 'burn_subtitle', 'merge')"""
        if action not in self.actions:
            self.actions.append(action)
    
    def remove_action(self, action: str):
        """Remove compression action"""
        if action in self.actions:
            self.actions.remove(action)
    
    def set_subtitle_file(self, file_path: str):
        """Set subtitle file path for burning"""
        self.subtitle_path = file_path
    
    def set_compression_option(self, key: str, value):
        """Set specific compression option"""
        self.compression_options[key] = value
    
    def get_all_options(self) -> Dict:
        """Get all session settings"""
        return {
            'link': self.link,
            'actions': self.actions,
            'subtitle': self.subtitle_path,
            'options': self.compression_options,
            'created_at': self.created_at.isoformat()
        }
    
    def is_valid(self) -> bool:
        """Check if session is valid for processing"""
        return bool(self.link and len(self.actions) > 0)
    
    def __repr__(self):
        return f"<UserCompressionSession user_id={self.user_id} actions={self.actions}>"


class SessionManager:
    """Global session manager for all users"""
    
    def __init__(self):
        self.sessions: Dict[int, UserCompressionSession] = {}
    
    def create_session(self, user_id: int) -> UserCompressionSession:
        """Create new session for user"""
        session = UserCompressionSession(user_id)
        self.sessions[user_id] = session
        return session
    
    def get_session(self, user_id: int) -> Optional[UserCompressionSession]:
        """Get existing session for user"""
        return self.sessions.get(user_id)
    
    def delete_session(self, user_id: int):
        """Delete user session"""
        if user_id in self.sessions:
            del self.sessions[user_id]
    
    def session_exists(self, user_id: int) -> bool:
        """Check if session exists"""
        return user_id in self.sessions
    
    def clear_all(self):
        """Clear all sessions"""
        self.sessions.clear()


# Global session manager instance
session_manager = SessionManager()
