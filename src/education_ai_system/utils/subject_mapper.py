import yaml
from pathlib import Path
from typing import Dict

class SubjectMapper:
    def __init__(self):
        self._load_mappings()
    
    def _load_mappings(self):
        """Load subject mappings from YAML config"""
        config_path = Path(__file__).parent.parent / "config" / "subject_mappings.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        self.standard_subjects = set(config['standard_subjects'])
        self.aliases = config['subject_aliases']
    
    def normalize_subject(self, subject: str) -> str:
        """Convert any subject input to standard form"""
        subject = subject.lower().strip()

        # Convert underscores to spaces FIRST
        subject = subject.replace("_", " ")
        
        # Return alias mapping if exists
        if subject in self.aliases:
            return self.aliases[subject]
        
        # Return as-is if it's already standard
        if subject in self.standard_subjects:
            return subject
        
        # Return as-is for unknown subjects (let Pinecone handle it)
        return subject
    
    def get_all_standard_subjects(self) -> list:
        """Get list of all standard subject names"""
        return list(self.standard_subjects)

# Global instance
subject_mapper = SubjectMapper()