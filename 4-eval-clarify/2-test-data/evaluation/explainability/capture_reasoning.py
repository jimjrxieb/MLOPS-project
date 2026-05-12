#!/usr/bin/env python3
"""
GP-CLARIFY: Chain-of-Thought Reasoning Capture
===============================================
Captures and analyzes JADE's reasoning process to understand WHY
she makes specific decisions, not just WHAT she decides.

This implements true explainability by:
1. Prompting JADE to "think step by step"
2. Extracting the reasoning chain
3. Comparing JADE's reasoning to expected security reasoning
4. Identifying gaps in JADE's thought process

Usage:
    python3 capture_reasoning.py --model jade:v0.4 --scenario "insecure-deployment"
    python3 capture_reasoning.py --model jade:v0.4 --batch ../2-test-data/integration-tests
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import argparse


@dataclass
class ReasoningStep:
    """A single step in JADE's reasoning chain."""
    step_number: int
    observation: str
    analysis: str
    conclusion: str
    confidence: str  # HIGH, MEDIUM, LOW
    keywords: List[str]


@dataclass
class ReasoningChain:
    """Complete reasoning chain for a decision."""
    scenario: str
    question: str
    steps: List[ReasoningStep]
    final_decision: str
    decision_confidence: str
    reasoning_quality: str  # STRONG, ADEQUATE, WEAK
    missing_considerations: List[str]


class ReasoningCapturer:
    """Capture and analyze JADE's chain-of-thought reasoning."""

    # Expected reasoning patterns for security analysis
    SECURITY_REASONING_PATTERNS = {
        "privileged_analysis": [
            "identify privileged mode",
            "explain container escape risk",
            "recommend removing privileged",
        ],
        "root_analysis": [
            "identify running as root",
            "explain privilege escalation risk",
            "recommend non-root user",
        ],
        "resource_analysis": [
            "identify missing limits",
            "explain DoS/resource exhaustion risk",
            "recommend resource constraints",
        ],
        "network_analysis": [
            "identify host network access",
            "explain network segmentation bypass",
            "recommend pod network",
        ],
        "secrets_analysis": [
            "identify hardcoded secrets",
            "explain credential exposure risk",
            "recommend external secret management",
        ],
    }

    # Keywords that indicate strong reasoning
    STRONG_REASONING_KEYWORDS = [
        "because", "therefore", "since", "risk", "attack surface",
        "defense in depth", "least privilege", "blast radius",
        "security context", "compliance", "CIS benchmark",
    ]

    def __init__(self, model: str = "jade:v0.4", timeout: int = 180):
        self.model = model
        self.timeout = timeout
        self.captured_chains = []

    def prompt_for_reasoning(self, scenario: str, content: str) -> str:
        """Construct a prompt that elicits chain-of-thought reasoning."""
        return f"""You are JADE, a security expert analyzing infrastructure code.

IMPORTANT: Think step by step and explain your reasoning process.
For each issue you find, explain:
1. WHAT you observed (the specific code/config)
2. WHY it's a security concern (the risk/attack vector)
3. WHAT you recommend (the fix and why it helps)

Analyze this {scenario}:

```
{content}
```

Provide your analysis with explicit reasoning for each finding.
Format each finding as:
OBSERVATION: [what you see]
ANALYSIS: [why it's a problem]
RECOMMENDATION: [what to do]
CONFIDENCE: [HIGH/MEDIUM/LOW]

Then provide your overall assessment."""

    def capture_reasoning(self, scenario: str, content: str) -> ReasoningChain:
        """Capture JADE's reasoning for a given scenario."""
        prompt = self.prompt_for_reasoning(scenario, content)
        response = self._query_model(prompt)

        steps = self._parse_reasoning_steps(response)
        final_decision = self._extract_final_decision(response)
        confidence = self._assess_confidence(response, steps)
        quality = self._assess_reasoning_quality(steps)
        missing = self._identify_missing_considerations(scenario, steps)

        chain = ReasoningChain(
            scenario=scenario,
            question=f"Analyze {scenario} for security issues",
            steps=steps,
            final_decision=final_decision,
            decision_confidence=confidence,
            reasoning_quality=quality,
            missing_considerations=missing,
        )

        self.captured_chains.append(chain)
        return chain

    def _query_model(self, prompt: str) -> str:
        """Query JADE model via ollama."""
        try:
            result = subprocess.run(
                ["ollama", "run", self.model],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "[TIMEOUT - Model took too long to respond]"
        except Exception as e:
            return f"[ERROR: {e}]"

    def _parse_reasoning_steps(self, response: str) -> List[ReasoningStep]:
        """Parse structured reasoning steps from JADE's response."""
        steps = []

        # Look for OBSERVATION/ANALYSIS/RECOMMENDATION blocks
        pattern = r"OBSERVATION:\s*(.+?)(?=ANALYSIS:|$)"
        analysis_pattern = r"ANALYSIS:\s*(.+?)(?=RECOMMENDATION:|$)"
        rec_pattern = r"RECOMMENDATION:\s*(.+?)(?=CONFIDENCE:|OBSERVATION:|$)"
        conf_pattern = r"CONFIDENCE:\s*(.+?)(?=OBSERVATION:|$)"

        observations = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
        analyses = re.findall(analysis_pattern, response, re.DOTALL | re.IGNORECASE)
        recommendations = re.findall(rec_pattern, response, re.DOTALL | re.IGNORECASE)
        confidences = re.findall(conf_pattern, response, re.DOTALL | re.IGNORECASE)

        # Zip together, handling mismatched lengths
        max_steps = max(len(observations), 1)

        for i in range(max_steps):
            obs = observations[i].strip() if i < len(observations) else ""
            ana = analyses[i].strip() if i < len(analyses) else ""
            rec = recommendations[i].strip() if i < len(recommendations) else ""
            conf = confidences[i].strip().upper() if i < len(confidences) else "MEDIUM"

            # Clean up confidence
            if "HIGH" in conf:
                conf = "HIGH"
            elif "LOW" in conf:
                conf = "LOW"
            else:
                conf = "MEDIUM"

            # Extract keywords from this step
            keywords = self._extract_keywords(f"{obs} {ana} {rec}")

            if obs or ana or rec:  # Only add if we have content
                steps.append(ReasoningStep(
                    step_number=i + 1,
                    observation=obs,
                    analysis=ana,
                    conclusion=rec,
                    confidence=conf,
                    keywords=keywords,
                ))

        # If no structured format found, try to parse numbered items
        if not steps:
            steps = self._parse_unstructured_reasoning(response)

        return steps

    def _parse_unstructured_reasoning(self, response: str) -> List[ReasoningStep]:
        """Parse reasoning from unstructured response."""
        steps = []

        # Try numbered items
        numbered = re.findall(
            r"(\d+)[.)]\s*(.+?)(?=\d+[.)]|$)",
            response,
            re.DOTALL
        )

        for i, (num, content) in enumerate(numbered):
            content = content.strip()
            keywords = self._extract_keywords(content)

            # Try to split into observation/analysis
            parts = content.split(".", 1)
            observation = parts[0].strip() if parts else content
            analysis = parts[1].strip() if len(parts) > 1 else ""

            steps.append(ReasoningStep(
                step_number=i + 1,
                observation=observation,
                analysis=analysis,
                conclusion="",
                confidence="MEDIUM",
                keywords=keywords,
            ))

        return steps

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract security-relevant keywords from text."""
        text_lower = text.lower()
        found = []

        for keyword in self.STRONG_REASONING_KEYWORDS:
            if keyword in text_lower:
                found.append(keyword)

        # Also check for security concepts
        security_concepts = [
            "privileged", "root", "escalation", "injection", "exposure",
            "vulnerability", "exploit", "attack", "threat", "risk",
            "compliance", "audit", "policy", "best practice",
        ]
        for concept in security_concepts:
            if concept in text_lower and concept not in found:
                found.append(concept)

        return found

    def _extract_final_decision(self, response: str) -> str:
        """Extract the final decision/recommendation from response."""
        # Look for summary/conclusion sections
        patterns = [
            r"(?:overall|summary|conclusion|recommendation)[:]\s*(.+?)(?:\n\n|$)",
            r"(?:in summary|to summarize|finally)[:, ]\s*(.+?)(?:\n\n|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()[:500]

        # Return last paragraph as fallback
        paragraphs = response.strip().split("\n\n")
        return paragraphs[-1][:500] if paragraphs else ""

    def _assess_confidence(self, response: str, steps: List[ReasoningStep]) -> str:
        """Assess overall confidence in JADE's reasoning."""
        if not steps:
            return "LOW"

        # Count high confidence steps
        high_conf = sum(1 for s in steps if s.confidence == "HIGH")
        low_conf = sum(1 for s in steps if s.confidence == "LOW")

        # Check for hedging language
        hedging_words = ["might", "could", "possibly", "maybe", "uncertain", "unclear"]
        hedging_count = sum(1 for word in hedging_words if word in response.lower())

        if high_conf > len(steps) / 2 and hedging_count < 3:
            return "HIGH"
        elif low_conf > len(steps) / 2 or hedging_count > 5:
            return "LOW"
        else:
            return "MEDIUM"

    def _assess_reasoning_quality(self, steps: List[ReasoningStep]) -> str:
        """Assess the quality of JADE's reasoning chain."""
        if not steps:
            return "WEAK"

        # Check for presence of analysis (not just observations)
        has_analysis = sum(1 for s in steps if s.analysis)

        # Check for security keywords
        total_keywords = sum(len(s.keywords) for s in steps)

        # Check for complete reasoning (observation + analysis + conclusion)
        complete_steps = sum(
            1 for s in steps
            if s.observation and s.analysis and s.conclusion
        )

        if complete_steps >= len(steps) * 0.7 and total_keywords >= len(steps) * 2:
            return "STRONG"
        elif has_analysis >= len(steps) * 0.5:
            return "ADEQUATE"
        else:
            return "WEAK"

    def _identify_missing_considerations(
        self, scenario: str, steps: List[ReasoningStep]
    ) -> List[str]:
        """Identify security considerations JADE should have mentioned but didn't."""
        missing = []

        # Collect all keywords from steps
        all_keywords = set()
        for step in steps:
            all_keywords.update(k.lower() for k in step.keywords)
            all_keywords.update(step.observation.lower().split())
            all_keywords.update(step.analysis.lower().split())

        # Check expected patterns based on scenario type
        if "deployment" in scenario.lower() or "pod" in scenario.lower():
            expected = [
                ("privileged", "privileged container analysis"),
                ("root", "running as root analysis"),
                ("resources", "resource limits analysis"),
                ("probes", "health probe analysis"),
                ("capabilities", "Linux capabilities analysis"),
            ]
            for keyword, description in expected:
                if keyword not in " ".join(all_keywords):
                    missing.append(description)

        if "secret" in scenario.lower() or "credential" in scenario.lower():
            expected = [
                ("rotation", "secret rotation strategy"),
                ("encryption", "encryption at rest"),
                ("vault", "external secret management"),
            ]
            for keyword, description in expected:
                if keyword not in " ".join(all_keywords):
                    missing.append(description)

        return missing[:5]  # Limit to top 5 missing items

    def compare_to_reference(
        self, chain: ReasoningChain, reference_reasoning: str
    ) -> Dict[str, Any]:
        """Compare JADE's reasoning to a reference (e.g., Claude's reasoning)."""
        # Extract key points from reference
        reference_keywords = self._extract_keywords(reference_reasoning)

        # Extract key points from JADE
        jade_keywords = set()
        for step in chain.steps:
            jade_keywords.update(step.keywords)

        # Calculate overlap
        overlap = set(reference_keywords) & jade_keywords
        missing_from_jade = set(reference_keywords) - jade_keywords
        extra_in_jade = jade_keywords - set(reference_keywords)

        alignment_score = len(overlap) / len(reference_keywords) if reference_keywords else 0

        return {
            "alignment_score": round(alignment_score * 100, 1),
            "shared_concepts": list(overlap),
            "jade_missing": list(missing_from_jade),
            "jade_extra": list(extra_in_jade),
            "jade_reasoning_quality": chain.reasoning_quality,
        }

    def generate_report(self) -> Dict[str, Any]:
        """Generate summary report of captured reasoning chains."""
        if not self.captured_chains:
            return {"error": "No reasoning chains captured"}

        quality_counts = {"STRONG": 0, "ADEQUATE": 0, "WEAK": 0}
        confidence_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        total_steps = 0
        all_missing = []

        for chain in self.captured_chains:
            quality_counts[chain.reasoning_quality] += 1
            confidence_counts[chain.decision_confidence] += 1
            total_steps += len(chain.steps)
            all_missing.extend(chain.missing_considerations)

        # Most common missing considerations
        from collections import Counter
        missing_counter = Counter(all_missing)

        return {
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "chains_captured": len(self.captured_chains),
            "reasoning_quality_distribution": quality_counts,
            "confidence_distribution": confidence_counts,
            "average_steps_per_chain": round(total_steps / len(self.captured_chains), 1),
            "top_missing_considerations": dict(missing_counter.most_common(10)),
            "chains": [asdict(c) for c in self.captured_chains],
        }


def main():
    parser = argparse.ArgumentParser(
        description="GP-CLARIFY: Chain-of-Thought Reasoning Capture"
    )
    parser.add_argument(
        "--model", "-m",
        default="jade:v0.4",
        help="Model to analyze (default: jade:v0.4)"
    )
    parser.add_argument(
        "--scenario", "-s",
        help="Scenario name (e.g., 'insecure-deployment')"
    )
    parser.add_argument(
        "--file", "-f",
        help="Path to file to analyze"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output path for reasoning report (JSON)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Timeout per query in seconds (default: 180)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("GP-CLARIFY: Chain-of-Thought Reasoning Capture")
    print("=" * 70)
    print(f"Model: {args.model}")

    capturer = ReasoningCapturer(model=args.model, timeout=args.timeout)

    if args.file:
        # Analyze specific file
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return 1

        with open(file_path) as f:
            content = f.read()

        scenario = args.scenario or file_path.stem
        print(f"\nCapturing reasoning for: {scenario}")

        chain = capturer.capture_reasoning(scenario, content)

        print(f"\n{'='*60}")
        print("REASONING CHAIN CAPTURED")
        print(f"{'='*60}")
        print(f"Steps identified: {len(chain.steps)}")
        print(f"Reasoning quality: {chain.reasoning_quality}")
        print(f"Decision confidence: {chain.decision_confidence}")

        if chain.steps:
            print("\nReasoning Steps:")
            for step in chain.steps:
                print(f"\n  Step {step.step_number}:")
                print(f"    Observation: {step.observation[:100]}...")
                print(f"    Analysis: {step.analysis[:100]}...")
                print(f"    Confidence: {step.confidence}")
                print(f"    Keywords: {', '.join(step.keywords[:5])}")

        if chain.missing_considerations:
            print(f"\nMissing Considerations:")
            for missing in chain.missing_considerations:
                print(f"  - {missing}")

        print(f"\nFinal Decision Preview:")
        print(f"  {chain.final_decision[:200]}...")

    else:
        print("\nNo file specified. Use --file to analyze a specific file.")
        print("Example: python3 capture_reasoning.py --file deployment-FAULTY.yaml")
        return 1

    # Generate report
    report = capturer.generate_report()

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\nReport saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
