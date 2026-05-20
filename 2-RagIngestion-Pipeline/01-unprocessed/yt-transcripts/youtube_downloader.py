#!/usr/bin/env python3
"""
YouTube Transcript Downloader for JADE Night Learning

Extracts transcripts from YouTube videos, preprocesses them,
and saves them as JSONL for HTC ingestion pipeline.

Author: Claude + Jimmie
Date: October 29, 2025
"""

import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
except ImportError:
    print("❌ youtube-transcript-api not installed!")
    print("   Run: pip install youtube-transcript-api")
    exit(1)

try:
    import yt_dlp
except ImportError:
    print("❌ yt-dlp not installed!")
    print("   Run: pip install yt-dlp")
    exit(1)


class YouTubeTranscriptDownloader:
    """Download and preprocess YouTube transcripts for JADE"""

    def __init__(self, output_dir: Path, chunk_size: int = 300, verbose: bool = True):
        """
        Args:
            output_dir: Where to save processed JSONL files
            chunk_size: Target words per chunk (default: 300)
            verbose: Print progress messages
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self.verbose = verbose

        # Concept categories for metadata extraction
        self.concept_categories = {
            'kubernetes': [
                'pod', 'deployment', 'service', 'ingress', 'configmap', 'secret',
                'namespace', 'daemonset', 'statefulset', 'pvc', 'pv', 'helm',
                'securityContext', 'runAsNonRoot', 'allowPrivilegeEscalation',
                'NetworkPolicy', 'RBAC', 'ServiceAccount', 'kubectl', 'k8s'
            ],
            'security': [
                'vulnerability', 'CVE', 'OWASP', 'CWE', 'privilege escalation',
                'authentication', 'authorization', 'encryption', 'TLS', 'HTTPS',
                'XSS', 'SQL injection', 'CSRF', 'security scanning', 'penetration testing',
                'zero trust', 'least privilege', 'defense in depth'
            ],
            'iac': [
                'terraform', 'cloudformation', 'ansible', 'pulumi', 'infrastructure as code',
                'IaC', 'provisioning', 'state management', 'modules', 'providers'
            ],
            'containers': [
                'docker', 'container', 'dockerfile', 'image', 'registry',
                'docker-compose', 'buildkit', 'multi-stage build', 'layer caching'
            ],
            'cicd': [
                'CI/CD', 'pipeline', 'jenkins', 'github actions', 'gitlab ci',
                'continuous integration', 'continuous deployment', 'automation',
                'testing', 'deployment', 'artifact'
            ],
            'cloud': [
                'AWS', 'Azure', 'GCP', 'S3', 'EC2', 'Lambda', 'EKS', 'AKS', 'GKE',
                'IAM', 'VPC', 'cloud security', 'cloud native'
            ],
            'policy': [
                'OPA', 'Open Policy Agent', 'Rego', 'Gatekeeper', 'admission control',
                'policy as code', 'compliance', 'constraints', 'validation'
            ]
        }

    def log(self, message: str):
        """Print message if verbose"""
        if self.verbose:
            print(message)

    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL

        Examples:
            https://www.youtube.com/watch?v=ABC123 → ABC123
            https://youtu.be/ABC123 → ABC123
        """
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([^&\n?#]+)',
            r'youtube\.com/embed/([^&\n?#]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        raise ValueError(f"Could not extract video ID from {url}")

    def get_video_metadata(self, video_url: str) -> Optional[Dict]:
        """
        Get video metadata using yt-dlp

        Returns:
            Dict with video_id, title, channel, duration, etc.
            None if failed
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

                return {
                    'video_id': info['id'],
                    'title': info['title'],
                    'channel': info['uploader'],
                    'duration': info.get('duration', 0),
                    'upload_date': info.get('upload_date', ''),
                    'description': info.get('description', '')[:500],  # First 500 chars
                    'categories': info.get('categories', []),
                    'tags': info.get('tags', [])[:20],  # Limit to 20 tags
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                }
        except Exception as e:
            self.log(f"❌ Failed to get metadata: {e}")
            return None

    def get_transcript(self, video_id: str) -> Optional[List[Dict]]:
        """
        Get transcript with timestamps

        Returns:
            List of dicts with 'text', 'start', 'duration'
            None if failed
        """
        try:
            # Create API instance
            ytt_api = YouTubeTranscriptApi()

            # Get list of available transcripts
            transcript_list = ytt_api.list(video_id)

            # Try to find English transcript (manual or auto-generated)
            try:
                transcript = transcript_list.find_transcript(['en'])
                return transcript.fetch()
            except:
                # Try auto-generated English
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                    return transcript.fetch()
                except:
                    self.log("   ❌ No English transcript available")
                    return None

        except TranscriptsDisabled:
            self.log("   ❌ Transcripts disabled for this video")
            return None
        except NoTranscriptFound:
            self.log("   ❌ No transcript found for this video")
            return None
        except Exception as e:
            self.log(f"   ❌ Transcript error: {e}")
            return None

    def format_timestamp(self, seconds: float) -> str:
        """Convert seconds to MM:SS or HH:MM:SS format"""
        td = timedelta(seconds=int(seconds))
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    def clean_text(self, text: str) -> str:
        """
        Clean transcript text
        - Remove [Music], [Applause], etc.
        - Fix spacing
        - Remove extra whitespace
        """
        # Remove annotations
        text = re.sub(r'\[.*?\]', '', text)
        text = re.sub(r'\(.*?\)', '', text)  # Remove (Music), (Laughter)

        # Fix multiple spaces
        text = re.sub(r'\s+', ' ', text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text

    def chunk_transcript(self, transcript: List[Dict], metadata: Dict) -> List[Dict]:
        """
        Chunk transcript into semantic segments

        Strategy:
        - Combine entries until ~chunk_size words
        - Preserve timestamp info
        """
        chunks = []
        current_chunk = {
            'text': '',
            'start_time': 0,
            'end_time': 0
        }

        word_count = 0

        for entry in transcript:
            text = entry.text.strip()

            # Start new chunk
            if word_count == 0:
                current_chunk['start_time'] = entry.start

            current_chunk['text'] += ' ' + text
            current_chunk['end_time'] = entry.start + entry.duration
            word_count += len(text.split())

            # Chunk is full
            if word_count >= self.chunk_size:
                cleaned_text = self.clean_text(current_chunk['text'])

                # Skip if too short after cleaning
                if len(cleaned_text.split()) < 50:
                    current_chunk = {'text': '', 'start_time': 0, 'end_time': 0}
                    word_count = 0
                    continue

                chunk = {
                    'content': cleaned_text,
                    'video_id': metadata['video_id'],
                    'video_title': metadata['title'],
                    'channel': metadata['channel'],
                    'timestamp': self.format_timestamp(current_chunk['start_time']),
                    'timestamp_url': f"https://youtu.be/{metadata['video_id']}?t={int(current_chunk['start_time'])}",
                    'start_seconds': current_chunk['start_time'],
                    'end_seconds': current_chunk['end_time']
                }

                chunks.append(chunk)

                # Reset for next chunk
                current_chunk = {'text': '', 'start_time': 0, 'end_time': 0}
                word_count = 0

        # Add final chunk if exists
        if current_chunk['text']:
            cleaned_text = self.clean_text(current_chunk['text'])
            if len(cleaned_text.split()) >= 50:  # At least 50 words
                chunk = {
                    'content': cleaned_text,
                    'video_id': metadata['video_id'],
                    'video_title': metadata['title'],
                    'channel': metadata['channel'],
                    'timestamp': self.format_timestamp(current_chunk['start_time']),
                    'timestamp_url': f"https://youtu.be/{metadata['video_id']}?t={int(current_chunk['start_time'])}",
                    'start_seconds': current_chunk['start_time'],
                    'end_seconds': current_chunk['end_time']
                }
                chunks.append(chunk)

        return chunks

    def extract_concepts(self, text: str) -> List[str]:
        """Extract technical concepts from text"""
        found_concepts = []
        text_lower = text.lower()

        for category, concepts in self.concept_categories.items():
            for concept in concepts:
                if concept.lower() in text_lower:
                    if concept not in found_concepts:
                        found_concepts.append(concept)

        return found_concepts

    def categorize_content(self, text: str, metadata: Dict) -> str:
        """Categorize content by primary topic"""
        text_lower = text.lower()
        title_lower = metadata['title'].lower()
        combined = text_lower + ' ' + title_lower

        category_scores = {}

        for category, concepts in self.concept_categories.items():
            score = sum(1 for concept in concepts if concept.lower() in combined)
            category_scores[category] = score

        # Return category with highest score
        if max(category_scores.values()) > 0:
            return max(category_scores, key=category_scores.get)
        else:
            return 'devops'

    def assess_difficulty(self, text: str, metadata: Dict) -> str:
        """Assess content difficulty level"""
        text_lower = text.lower()
        title_lower = metadata['title'].lower()
        combined = text_lower + ' ' + title_lower

        beginner_markers = [
            'introduction', 'basics', 'getting started', 'tutorial',
            'beginner', 'fundamentals', 'overview', 'what is'
        ]
        advanced_markers = [
            'deep dive', 'internals', 'architecture', 'advanced',
            'expert', 'production', 'optimization', 'performance tuning'
        ]

        beginner_score = sum(1 for marker in beginner_markers if marker in combined)
        advanced_score = sum(1 for marker in advanced_markers if marker in combined)

        if beginner_score > advanced_score:
            return 'beginner'
        elif advanced_score > beginner_score:
            return 'advanced'
        else:
            return 'intermediate'

    def create_qa_pairs(self, chunk: Dict, metadata: Dict) -> List[Dict]:
        """
        Create Q&A pairs for HTC ingestion

        Format matches HTC expected format:
        {"messages": [...], "metadata": {...}}
        """
        content = chunk['content']

        # Extract key concepts
        concepts = self.extract_concepts(content)
        topic = self.categorize_content(content, metadata)
        difficulty = self.assess_difficulty(content, metadata)

        # Create Q&A pair
        qa_pair = {
            "messages": [
                {
                    "role": "system",
                    "content": f"You are JADE, an expert in {topic} and cloud security."
                },
                {
                    "role": "user",
                    "content": f"Explain {', '.join(concepts[:3]) if concepts else topic} in the context of {metadata['title']}."
                },
                {
                    "role": "assistant",
                    "content": content
                }
            ],
            "metadata": {
                "source": "youtube",
                "video_id": chunk['video_id'],
                "video_title": metadata['title'],
                "channel": metadata['channel'],
                "timestamp": chunk['timestamp'],
                "timestamp_url": chunk['timestamp_url'],
                "topic": topic,
                "concepts": concepts,
                "difficulty": difficulty,
                "ingestion_date": datetime.now().isoformat(),
                "chunk_index": None  # Will be set by caller
            }
        }

        return [qa_pair]

    def download_video(self, video_url: str) -> bool:
        """
        Download and process single video

        Returns:
            True if successful, False otherwise
        """
        self.log(f"\n📺 Processing: {video_url}")

        try:
            # Step 1: Extract video ID
            video_id = self.extract_video_id(video_url)
            self.log(f"   Video ID: {video_id}")

            # Step 2: Get metadata
            self.log("   ├─ Fetching metadata...")
            metadata = self.get_video_metadata(video_url)
            if not metadata:
                self.log("   └─ ❌ Failed to get metadata")
                return False

            self.log(f"   │  Title: {metadata['title']}")
            self.log(f"   │  Channel: {metadata['channel']}")
            self.log(f"   │  Duration: {metadata['duration'] // 60} minutes")

            # Step 3: Get transcript
            self.log("   ├─ Fetching transcript...")
            transcript = self.get_transcript(video_id)
            if not transcript:
                self.log("   └─ ❌ No transcript available")
                return False

            self.log(f"   │  Transcript entries: {len(transcript)}")

            # Step 4: Chunk transcript
            self.log("   ├─ Chunking transcript...")
            chunks = self.chunk_transcript(transcript, metadata)
            self.log(f"   │  Created {len(chunks)} chunks")

            if len(chunks) == 0:
                self.log("   └─ ❌ No valid chunks created")
                return False

            # Step 5: Create Q&A pairs
            self.log("   ├─ Creating Q&A pairs...")
            qa_pairs = []
            for i, chunk in enumerate(chunks):
                pairs = self.create_qa_pairs(chunk, metadata)
                for pair in pairs:
                    pair['metadata']['chunk_index'] = i
                    qa_pairs.append(pair)

            self.log(f"   │  Created {len(qa_pairs)} Q&A pairs")

            # Step 6: Save to JSONL
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = re.sub(r'[^\w\-]', '_', metadata['title'][:50])
            output_file = self.output_dir / f"youtube_{video_id}_{safe_title}_{timestamp}.jsonl"

            self.log(f"   ├─ Saving to {output_file.name}...")
            with open(output_file, 'w', encoding='utf-8') as f:
                for pair in qa_pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + '\n')

            self.log(f"   └─ ✅ Saved {len(qa_pairs)} Q&A pairs")
            self.log(f"\n✨ Success: {metadata['title']}")
            return True

        except Exception as e:
            self.log(f"   └─ ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def download_playlist(self, playlist_url: str) -> Dict[str, int]:
        """
        Download all videos from a playlist

        Returns:
            Dict with 'success' and 'failed' counts
        """
        self.log(f"\n📋 Processing playlist: {playlist_url}")

        try:
            # Extract video URLs from playlist
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # Don't download, just get URLs
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)

                if 'entries' not in playlist_info:
                    self.log("❌ No videos found in playlist")
                    return {'success': 0, 'failed': 0}

                video_urls = []
                for entry in playlist_info['entries']:
                    if entry:
                        video_urls.append(f"https://www.youtube.com/watch?v={entry['id']}")

                self.log(f"   Found {len(video_urls)} videos in playlist")
                self.log(f"   Playlist: {playlist_info.get('title', 'Unknown')}\n")

        except Exception as e:
            self.log(f"❌ Failed to process playlist: {e}")
            return {'success': 0, 'failed': 0}

        # Download each video
        stats = {'success': 0, 'failed': 0}

        for i, video_url in enumerate(video_urls, 1):
            self.log(f"\n[{i}/{len(video_urls)}]")

            success = self.download_video(video_url)

            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1

            # Rate limiting (YouTube API has limits)
            if i < len(video_urls):
                time.sleep(2)  # 2 second delay between videos

        return stats


if __name__ == "__main__":
    # Test with a single video
    output_dir = Path(__file__).parent.parent / "unprocessed" / "night-learning"
    downloader = YouTubeTranscriptDownloader(output_dir=output_dir, verbose=True)

    test_video = "https://www.youtube.com/watch?v=oBf5lrmquYI"  # Example K8s security video
    downloader.download_video(test_video)
