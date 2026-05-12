"""
Base LLM Provider Interface

This defines the contract that all LLM providers must implement.
Allows JADE to work with any LLM backend (Ollama, OpenAI, Anthropic, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Iterator


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement:
    - generate() - Single-turn text generation
    - chat() - Multi-turn conversation
    - stream() - Streaming responses (optional, can return generator or None)
    - is_available() - Health check
    - get_model_info() - Model metadata

    Example:
        >>> from providers import OllamaProvider
        >>> provider = OllamaProvider(model="jade:v0.8")
        >>> response = provider.generate("How do I drain a Kubernetes node?")
    """

    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize provider.

        Args:
            model_name: Model identifier (e.g., "jade:v0.8", "gpt-4", "claude-sonnet-4-5")
            config: Provider-specific configuration
        """
        self.model_name = model_name
        self.config = config or {}

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate text from a single prompt.

        Args:
            prompt: User prompt or question
            system_prompt: Optional system message to set context
            max_tokens: Maximum tokens to generate
            temperature: 0.0 (factual) to 1.0 (creative)
            **kwargs: Provider-specific parameters

        Returns:
            Generated text response

        Example:
            >>> response = provider.generate(
            ...     "How do I drain a node?",
            ...     system_prompt="You are a CKS expert.",
            ...     temperature=0.3
            ... )
        """
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Multi-turn chat with conversation history.

        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            max_tokens: Maximum tokens to generate
            temperature: Creativity level
            **kwargs: Provider-specific parameters

        Returns:
            Assistant's response

        Example:
            >>> messages = [
            ...     {"role": "system", "content": "You are a Kubernetes expert."},
            ...     {"role": "user", "content": "What is a pod?"},
            ...     {"role": "assistant", "content": "A pod is..."},
            ...     {"role": "user", "content": "How do I deploy one?"}
            ... ]
            >>> response = provider.chat(messages, temperature=0.3)
        """
        pass

    def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        temperature: float = 0.7,
        **kwargs
    ) -> Optional[Iterator[str]]:
        """
        Stream text generation (optional).

        Providers can override this to support streaming.
        If not supported, returns None and caller should use generate() instead.

        Args:
            prompt: User prompt
            system_prompt: Optional system message
            max_tokens: Maximum tokens
            temperature: Creativity level
            **kwargs: Provider-specific parameters

        Returns:
            Iterator yielding text chunks, or None if streaming not supported

        Example:
            >>> stream = provider.stream("Explain Kubernetes")
            >>> if stream:
            ...     for chunk in stream:
            ...         print(chunk, end='', flush=True)
            ... else:
            ...     # Fallback to non-streaming
            ...     print(provider.generate("Explain Kubernetes"))
        """
        return None  # Default: streaming not supported

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is available and ready.

        Returns:
            True if provider can generate responses

        Example:
            >>> if provider.is_available():
            ...     response = provider.generate(prompt)
            ... else:
            ...     print("Provider not available")
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model and provider metadata.

        Returns:
            Dictionary with model information:
            - provider: Provider name (e.g., "ollama", "openai", "anthropic")
            - model: Model name
            - available: Whether model is ready
            - backend: Backend type
            - Additional provider-specific info

        Example:
            >>> info = provider.get_model_info()
            >>> print(f"{info['provider']}: {info['model']}")
            >>> print(f"Available: {info['available']}")
        """
        pass

    # ============================================================
    # OPTIONAL HELPER METHODS (can be overridden)
    # ============================================================

    def query_knowledge(
        self,
        question: str,
        context: Optional[str] = None,
        temperature: float = 0.3
    ) -> str:
        """
        Answer questions using RAG-provided context.

        Default implementation uses generate() with context injection.
        Providers can override for custom RAG integration.

        Args:
            question: User's question
            context: Retrieved context from RAG
            temperature: Low for factual answers

        Returns:
            Answer based on context
        """
        system_prompt = """You are JADE (also known as SCDAO from training data - same identity).
A senior DevSecOps consultant with expertise in:
- Kubernetes (CKS certified)
- Infrastructure as Code (Terraform, CloudFormation)
- Security scanning (Trivy, Bandit, Semgrep, Gitleaks)
- Policy as Code (OPA/Rego, Gatekeeper)
- Compliance frameworks (SOC2, PCI-DSS, CIS, NIST)
- Cloud security (AWS, Azure, GCP)

Provide accurate, professional answers based on the context provided.
If context doesn't contain the answer, say so - don't make up information."""

        if context:
            prompt = f"""Context from knowledge base:
{context}

Question: {question}

Answer:"""
        else:
            prompt = question

        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=600
        )

    def security_analysis(
        self,
        code_content: str,
        file_type: str = "terraform",
        temperature: float = 0.2
    ) -> str:
        """
        Generate security analysis for code.

        Default implementation uses generate() with security prompts.
        Providers can override for custom security analysis.

        Args:
            code_content: Code to analyze
            file_type: "terraform", "kubernetes", "python", etc.
            temperature: Low for consistent analysis

        Returns:
            Security analysis report
        """
        system_prompt = self._get_security_system_prompt(file_type)
        prompt = self._get_security_prompt(code_content, file_type)

        return self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=800
        )

    def _get_security_system_prompt(self, file_type: str) -> str:
        """Get system prompt for security analysis"""
        if file_type == "terraform":
            return """You are a senior security consultant specializing in Infrastructure as Code (IaC) security.
You have deep expertise in:
- Terraform security best practices
- CIS benchmarks for cloud infrastructure
- SOC2, PCI-DSS, HIPAA compliance
- Cloud security (AWS, Azure, GCP)
- Zero-trust architecture

Analyze code for security vulnerabilities and provide actionable remediation steps."""

        elif file_type == "kubernetes":
            return """You are a Certified Kubernetes Security Specialist (CKS).
You have deep expertise in:
- Pod Security Standards (Baseline, Restricted)
- Kubernetes RBAC and admission control
- Network policies and service mesh security
- Container security and image scanning
- Secrets management

Analyze configurations for security issues and provide CKS-aligned recommendations."""

        elif file_type == "python":
            return """You are a senior application security engineer specializing in Python.
You have deep expertise in:
- OWASP Top 10 vulnerabilities
- Python security best practices
- Secure coding patterns
- Dependency vulnerability management
- SAST/DAST methodologies

Analyze code for security vulnerabilities and suggest secure alternatives."""

        else:
            return "You are a security consultant. Analyze code for security vulnerabilities."

    def _get_security_prompt(self, code_content: str, file_type: str) -> str:
        """Get analysis prompt for security review"""
        # Limit code context to prevent token overflow
        code_snippet = code_content[:3000]

        if file_type == "terraform":
            return f"""Analyze this Terraform configuration for security issues:

```hcl
{code_snippet}
```

Focus on:
1. Hardcoded credentials and secrets
2. Overpermissive access (0.0.0.0/0, wildcard permissions)
3. Missing encryption configurations
4. Public access to sensitive resources
5. IAM policy misconfigurations
6. Network security gaps

Provide:
- Critical issues found (HIGH/CRITICAL severity)
- Compliance violations (CIS, SOC2, PCI-DSS)
- Specific remediation steps with code examples

Analysis:"""

        elif file_type == "kubernetes":
            return f"""Analyze this Kubernetes configuration for security issues:

```yaml
{code_snippet}
```

Focus on:
1. Pod Security Standard violations
2. Privileged containers and dangerous capabilities
3. Missing security contexts (runAsNonRoot, readOnlyRootFilesystem)
4. Network policy gaps
5. RBAC misconfigurations
6. Secret management issues

Provide:
- PSS violations (Baseline/Restricted)
- CKS exam-relevant issues
- Specific remediation YAML examples

Analysis:"""

        elif file_type == "python":
            return f"""Analyze this Python code for security vulnerabilities:

```python
{code_snippet}
```

Focus on:
1. Injection vulnerabilities (SQL, command, code injection)
2. Hardcoded credentials
3. Insecure cryptography
4. Authentication/authorization issues
5. Unsafe deserialization
6. Path traversal vulnerabilities

Provide:
- OWASP Top 10 violations
- CWE mappings
- Secure code examples for remediation

Analysis:"""

        else:
            return f"""Analyze this code for security issues:

```
{code_snippet}
```

Provide security analysis and recommendations:"""
