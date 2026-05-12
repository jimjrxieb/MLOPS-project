#!/usr/bin/env python3
"""
User Feedback System for Jade RAG
Allows thumbs up/down to boost confidence on future retrievals
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class FeedbackSystem:
    """Track user feedback to improve RAG confidence"""

    def __init__(self, feedback_file: str = "~/.jade/feedback.jsonl"):
        self.feedback_file = Path(feedback_file).expanduser()
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)

        # Create if doesn't exist
        if not self.feedback_file.exists():
            self.feedback_file.touch()

    def record_feedback(
        self,
        query: str,
        document_id: str,
        document_content: str,
        feedback: str,  # "thumbs_up" or "thumbs_down"
        collection: str = "unknown"
    ):
        """Record user feedback on a retrieved document"""

        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "document_id": document_id,
            "document_content": document_content[:500],  # First 500 chars
            "collection": collection,
            "feedback": feedback,
            "boost_factor": 1.5 if feedback == "thumbs_up" else 0.5  # 50% boost or 50% penalty
        }

        # Append to JSONL file
        with open(self.feedback_file, 'a') as f:
            f.write(json.dumps(feedback_entry) + '\n')

        print(f"✅ Feedback recorded: {feedback} for query '{query[:50]}...'")

    def get_boost_factor(self, query: str, document_content: str) -> float:
        """Get boost factor based on historical feedback"""

        if not self.feedback_file.exists():
            return 1.0  # No boost

        boost_factors = []

        # Read all feedback
        with open(self.feedback_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                entry = json.loads(line)

                # Check if this document was previously rated for similar query
                query_similarity = self._calculate_similarity(query, entry['query'])
                content_similarity = self._calculate_similarity(document_content[:500], entry['document_content'])

                # If both query and content are similar, apply boost
                if query_similarity > 0.7 and content_similarity > 0.8:
                    boost_factors.append(entry['boost_factor'])

        # Average all applicable boost factors
        if boost_factors:
            avg_boost = sum(boost_factors) / len(boost_factors)
            print(f"📈 Applying boost factor {avg_boost:.2f} based on {len(boost_factors)} past feedback(s)")
            return avg_boost

        return 1.0  # No boost

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Simple Jaccard similarity for feedback matching"""

        # Tokenize
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        # Jaccard similarity
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def get_feedback_stats(self) -> Dict[str, int]:
        """Get statistics on user feedback"""

        stats = {
            "total_feedback": 0,
            "thumbs_up": 0,
            "thumbs_down": 0,
            "collections": {}
        }

        if not self.feedback_file.exists():
            return stats

        with open(self.feedback_file, 'r') as f:
            for line in f:
                if not line.strip():
                    continue

                entry = json.loads(line)
                stats["total_feedback"] += 1

                if entry["feedback"] == "thumbs_up":
                    stats["thumbs_up"] += 1
                else:
                    stats["thumbs_down"] += 1

                coll = entry.get("collection", "unknown")
                stats["collections"][coll] = stats["collections"].get(coll, 0) + 1

        return stats


# Singleton instance
_feedback_system: Optional[FeedbackSystem] = None

def get_feedback_system() -> FeedbackSystem:
    """Get singleton feedback system instance"""
    global _feedback_system
    if _feedback_system is None:
        _feedback_system = FeedbackSystem()
    return _feedback_system


if __name__ == "__main__":
    print("🧪 Testing Feedback System\n")

    fs = get_feedback_system()

    # Simulate feedback
    fs.record_feedback(
        query="What is a Kubernetes cluster?",
        document_id="doc_123",
        document_content="A Kubernetes cluster is a set of nodes that run containerized applications...",
        feedback="thumbs_up",
        collection="documentation"
    )

    # Check boost
    boost = fs.get_boost_factor(
        query="What is Kubernetes?",
        document_content="A Kubernetes cluster is a set of nodes that run containerized applications..."
    )

    print(f"\n📊 Boost factor for similar query: {boost:.2f}")

    # Get stats
    stats = fs.get_feedback_stats()
    print(f"\n📈 Feedback Stats:")
    print(f"   Total: {stats['total_feedback']}")
    print(f"   👍 Thumbs Up: {stats['thumbs_up']}")
    print(f"   👎 Thumbs Down: {stats['thumbs_down']}")
