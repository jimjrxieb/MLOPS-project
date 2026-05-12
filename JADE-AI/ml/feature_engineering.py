"""
Feature Engineering for Security Findings
Transforms raw finding dicts into ML-ready feature vectors
"""

import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.preprocessing import LabelEncoder, StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.compose import ColumnTransformer


class FindingFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extract features from security findings for ML classification.

    Transforms a finding dict into a feature vector combining:
    - Categorical features (scanner, severity, file_type)
    - Text features (description, rule_id TF-IDF)
    - Numeric features (file_count, line_count, has_fix)
    - Pattern features (CVE presence, OWASP category)
    """

    # Known scanners for one-hot encoding
    KNOWN_SCANNERS = [
        'bandit', 'semgrep', 'trivy', 'grype', 'snyk', 'gitleaks',
        'checkov', 'tfsec', 'conftest', 'kubescape', 'polaris',
        'kube-bench', 'eslint', 'hadolint', 'prowler', 'unknown'
    ]

    # Severity levels
    SEVERITIES = ['critical', 'high', 'medium', 'low', 'info', 'unknown']

    # OWASP Top 10 patterns
    OWASP_PATTERNS = {
        'A01': r'broken.access|auth.*bypass|idor|privilege',
        'A02': r'crypto|weak.*cipher|md5|sha1|encrypt',
        'A03': r'injection|sql|xss|command|ldap|xpath',
        'A04': r'insecure.design|threat.model',
        'A05': r'misconfig|default|hardcoded|exposed',
        'A06': r'vulnerable.*component|outdated|cve-|ghsa-',
        'A07': r'auth.*fail|brute|credential|session',
        'A08': r'deserial|integrity|sign.*verify',
        'A09': r'log.*inject|monitor|audit',
        'A10': r'ssrf|request.*forgery|redirect'
    }

    # Complexity indicators
    COMPLEXITY_INDICATORS = {
        'trivial': r'format|indent|whitespace|semi|quote',
        'simple': r'remove|delete|update|upgrade|pin',
        'moderate': r'refactor|rewrite|multiple|files',
        'complex': r'architect|redesign|multi.*service|cross.*cluster',
        'critical': r'zero.*trust|compliance|encryption.*rest|iam.*policy'
    }

    def __init__(self, max_text_features: int = 100):
        """
        Initialize feature extractor.

        Args:
            max_text_features: Max TF-IDF features from text
        """
        self.max_text_features = max_text_features
        self.tfidf = None  # Initialized in fit() based on data size
        self.scanner_encoder = None
        self.severity_encoder = None
        self._fitted = False

    def fit(self, findings: List[Dict[str, Any]], y=None):
        """Fit the feature extractor on training data."""
        # Fit TF-IDF on descriptions with adaptive min_df
        descriptions = [self._get_text(f) for f in findings]
        if descriptions:
            # Adjust min_df based on dataset size
            n_docs = len(descriptions)
            min_df = 1 if n_docs < 5 else min(2, n_docs // 2)

            self.tfidf = TfidfVectorizer(
                max_features=self.max_text_features,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=min_df
            )
            try:
                self.tfidf.fit(descriptions)
            except ValueError:
                # Fallback: no min_df constraint
                self.tfidf = TfidfVectorizer(
                    max_features=self.max_text_features,
                    stop_words='english',
                    ngram_range=(1, 1),
                    min_df=1
                )
                self.tfidf.fit(descriptions)

        # Create one-hot encoders
        self.scanner_encoder = {s: i for i, s in enumerate(self.KNOWN_SCANNERS)}
        self.severity_encoder = {s: i for i, s in enumerate(self.SEVERITIES)}

        self._fitted = True
        return self

    def transform(self, findings: List[Dict[str, Any]]) -> np.ndarray:
        """Transform findings into feature matrix."""
        if not self._fitted:
            raise ValueError("FeatureExtractor not fitted. Call fit() first.")

        features = []
        for finding in findings:
            features.append(self._extract_single(finding))

        return np.array(features)

    def fit_transform(self, findings: List[Dict[str, Any]], y=None) -> np.ndarray:
        """Fit and transform in one step."""
        self.fit(findings, y)
        return self.transform(findings)

    def _extract_single(self, finding: Dict[str, Any]) -> np.ndarray:
        """Extract features from a single finding."""
        features = []

        # === Categorical Features ===
        # Scanner one-hot (16 features)
        scanner = self._normalize_scanner(finding.get('scanner', 'unknown'))
        scanner_idx = self.scanner_encoder.get(scanner, len(self.KNOWN_SCANNERS) - 1)
        scanner_onehot = [1.0 if i == scanner_idx else 0.0 for i in range(len(self.KNOWN_SCANNERS))]
        features.extend(scanner_onehot)

        # Severity one-hot (6 features)
        severity = finding.get('severity', 'unknown').lower()
        severity_idx = self.severity_encoder.get(severity, len(self.SEVERITIES) - 1)
        severity_onehot = [1.0 if i == severity_idx else 0.0 for i in range(len(self.SEVERITIES))]
        features.extend(severity_onehot)

        # === Numeric Features ===
        # Has fix available (1 feature)
        has_fix = 1.0 if finding.get('fixed_version') or finding.get('fix_suggestion') else 0.0
        features.append(has_fix)

        # File count (1 feature) - multi-file changes are more complex
        file_count = len(finding.get('files', [])) if isinstance(finding.get('files'), list) else 1
        features.append(min(file_count / 10.0, 1.0))  # Normalize to 0-1

        # Line number (1 feature) - higher line numbers might indicate deeper code
        line = finding.get('line', 0)
        features.append(min(line / 1000.0, 1.0) if line else 0.0)

        # === Pattern Features ===
        description = self._get_text(finding).lower()
        rule_id = finding.get('rule_id', '').lower()

        # CVE pattern (1 feature)
        has_cve = 1.0 if re.search(r'cve-\d{4}-\d+', description + rule_id) else 0.0
        features.append(has_cve)

        # GHSA pattern (1 feature)
        has_ghsa = 1.0 if re.search(r'ghsa-[a-z0-9]+-[a-z0-9]+', description + rule_id) else 0.0
        features.append(has_ghsa)

        # OWASP category detection (10 features)
        for category, pattern in self.OWASP_PATTERNS.items():
            match = 1.0 if re.search(pattern, description, re.I) else 0.0
            features.append(match)

        # Complexity indicators (5 features)
        for level, pattern in self.COMPLEXITY_INDICATORS.items():
            match = 1.0 if re.search(pattern, description, re.I) else 0.0
            features.append(match)

        # === File Type Features ===
        file_path = finding.get('file', '')
        file_features = self._extract_file_type(file_path)
        features.extend(file_features)

        # === Text TF-IDF Features ===
        try:
            if self.tfidf is not None:
                text = self._get_text(finding)
                tfidf_features = self.tfidf.transform([text]).toarray()[0]
                features.extend(tfidf_features)
                # Pad to max_text_features if needed
                if len(tfidf_features) < self.max_text_features:
                    features.extend([0.0] * (self.max_text_features - len(tfidf_features)))
            else:
                # No TF-IDF fitted, add zeros
                features.extend([0.0] * self.max_text_features)
        except Exception:
            # If TF-IDF fails, add zeros
            features.extend([0.0] * self.max_text_features)

        return np.array(features, dtype=np.float32)

    def _normalize_scanner(self, scanner: str) -> str:
        """Normalize scanner name."""
        scanner = scanner.lower().replace('npc', '').strip()
        return scanner if scanner in self.KNOWN_SCANNERS else 'unknown'

    def _get_text(self, finding: Dict[str, Any]) -> str:
        """Combine text fields for TF-IDF."""
        parts = [
            finding.get('description', ''),
            finding.get('title', ''),
            finding.get('rule_id', ''),
            finding.get('message', '')
        ]
        return ' '.join(str(p) for p in parts if p)

    def _extract_file_type(self, file_path: str) -> List[float]:
        """Extract file type features (8 categories)."""
        file_types = {
            'python': r'\.(py|pyx)$',
            'javascript': r'\.(js|jsx|ts|tsx)$',
            'yaml': r'\.(ya?ml)$',
            'dockerfile': r'(dockerfile|\.dockerfile)$',
            'terraform': r'\.(tf|tfvars)$',
            'kubernetes': r'(deployment|service|ingress|configmap).*\.ya?ml$',
            'shell': r'\.(sh|bash)$',
            'config': r'\.(json|toml|ini|cfg|conf)$'
        }

        features = []
        file_lower = file_path.lower()
        for _, pattern in file_types.items():
            match = 1.0 if re.search(pattern, file_lower, re.I) else 0.0
            features.append(match)

        return features

    def get_feature_names(self) -> List[str]:
        """Get list of feature names for interpretability."""
        names = []

        # Scanner features
        names.extend([f'scanner_{s}' for s in self.KNOWN_SCANNERS])

        # Severity features
        names.extend([f'severity_{s}' for s in self.SEVERITIES])

        # Numeric features
        names.extend(['has_fix', 'file_count', 'line_number'])

        # Pattern features
        names.extend(['has_cve', 'has_ghsa'])
        names.extend([f'owasp_{cat}' for cat in self.OWASP_PATTERNS.keys()])
        names.extend([f'complexity_{level}' for level in self.COMPLEXITY_INDICATORS.keys()])

        # File type features
        names.extend(['file_python', 'file_javascript', 'file_yaml', 'file_dockerfile',
                     'file_terraform', 'file_kubernetes', 'file_shell', 'file_config'])

        # TF-IDF features
        if hasattr(self.tfidf, 'get_feature_names_out'):
            names.extend([f'tfidf_{w}' for w in self.tfidf.get_feature_names_out()])
        else:
            names.extend([f'tfidf_{i}' for i in range(self.max_text_features)])

        return names


class FindingBatchTransformer(BaseEstimator, TransformerMixin):
    """
    Wrapper for batch processing of findings.
    Handles dict input and converts to feature matrix.
    """

    def __init__(self, extractor: FindingFeatureExtractor = None):
        self.extractor = extractor or FindingFeatureExtractor()

    def fit(self, X, y=None):
        if isinstance(X, list) and len(X) > 0 and isinstance(X[0], dict):
            self.extractor.fit(X, y)
        return self

    def transform(self, X):
        if isinstance(X, list) and len(X) > 0 and isinstance(X[0], dict):
            return self.extractor.transform(X)
        return X
