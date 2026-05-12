"""
LLM Provider Factory

Creates LLM provider instances based on configuration.
Supports Ollama (jade:v1.0 - primary), Anthropic (fallback), OpenAI, and Gemini.

This is the main entry point for JADE to get an LLM provider.

Plug-and-Play via Environment Variables:
    JADE_PROVIDER=ollama|anthropic|openai|gemini
    JADE_MODEL=jade:v1.0|claude-haiku-4-5-20251001|gpt-4|gemini-pro
"""

import yaml
import os
from pathlib import Path
from typing import Optional, Dict, Any
# Provider imports (JADE-AI/ is in sys.path when jade.py runs)
try:
    from providers.base import BaseLLMProvider
    from providers.ollama import OllamaProvider
    from providers.openai import OpenAIProvider
    from providers.anthropic import AnthropicProvider
    from providers.gemini import GeminiProvider
except ImportError:
    from ..providers.base import BaseLLMProvider
    from ..providers.ollama import OllamaProvider
    from ..providers.openai import OpenAIProvider
    from ..providers.anthropic import AnthropicProvider
    from ..providers.gemini import GeminiProvider

# Import centralized paths
try:
    from paths import GP_CHROMA_PATH
except ImportError:
    try:
        from .paths import GP_CHROMA_PATH
    except ImportError:
        GP_CHROMA_PATH = Path(__file__).parent.parent.parent / "GP-OPENSEARCH" / "05-ragged-data" / "chroma"


def load_jade_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load JADE configuration from YAML file.

    Args:
        config_path: Path to jade_config.yaml (default: JADE-AI/config/jade_config.yaml)

    Returns:
        Configuration dictionary

    Example:
        >>> config = load_jade_config()
        >>> print(config['llm']['provider'])
        'ollama'
    """
    if config_path is None:
        # Default path: JADE-AI/config/jade_config.yaml
        jade_root = Path(__file__).parent.parent
        config_path = jade_root / "config" / "jade_config.yaml"

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            return config or {}
    except FileNotFoundError:
        print(f"⚠️  Config file not found: {config_path}")
        print("   Using default configuration (Ollama jade:v1.0)")
        return _get_default_config()
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        print("   Using default configuration")
        return _get_default_config()


def _get_default_config() -> Dict[str, Any]:
    """Get default JADE configuration"""
    return {
        'llm': {
            'provider': 'ollama',
            'ollama': {
                'base_url': 'http://localhost:11434',
                'model': 'jade:v1.0',
                'fallback': 'jade:v0.9',
                'timeout': 120
            },
            'anthropic': {
                'api_key_env': 'ANTHROPIC_API_KEY',
                'model': 'claude-haiku-4-5-20251001',
                'timeout': 120
            }
        },
        'rag': {
            'enabled': True,
            'db_path': str(GP_CHROMA_PATH),
            'top_k': 5
        },
        'memory': {
            'enabled': True,
            'max_history': 20,
            'persist': True
        }
    }


def create_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None
) -> BaseLLMProvider:
    """
    Create LLM provider instance, attempting providers in a configured priority order.
    """
    jade_config = load_jade_config(config_path)
    llm_config = jade_config.get('llm', {})

    # Determine desired provider and priority list
    # Env var JADE_PROVIDER overrides everything
    initial_provider_name = os.environ.get("JADE_PROVIDER")
    if initial_provider_name:
        provider_priority = [initial_provider_name.lower()]
    else:
        # Use configured priority list, or default if not present
        provider_priority = llm_config.get('provider_priority', ['ollama', 'anthropic', 'gemini', 'openai'])
        # If llm.provider is set in config and not in priority list, ensure it's at the front
        if llm_config.get('provider') and llm_config['provider'] not in provider_priority:
             provider_priority.insert(0, llm_config['provider'])


    initialized_provider = None
    for p_name in provider_priority:
        p_name = p_name.lower()
        temp_provider = None
        try:
            if p_name == 'ollama':
                temp_provider = _create_ollama_provider(model_name, config, llm_config)
            elif p_name == 'openai':
                temp_provider = _create_openai_provider(model_name, config, llm_config)
            elif p_name == 'anthropic':
                temp_provider = _create_anthropic_provider(model_name, config, llm_config)
            elif p_name == 'gemini':
                temp_provider = _create_gemini_provider(model_name, config, llm_config)
            else:
                print(f"⚠️  Skipping unknown provider in priority list: {p_name}")
                continue

            if temp_provider and temp_provider.is_available():
                print(f"✅ Successfully initialized LLM provider: {p_name} ({temp_provider.get_model_info()['model']})")
                initialized_provider = temp_provider
                break
            elif temp_provider:
                print(f"❌ Provider {p_name} ({temp_provider.get_model_info()['model']}) is not available. Trying next...")
            else:
                # If temp_provider is None, means create_provider helper failed
                print(f"❌ Failed to create provider {p_name}. Trying next...")

        except Exception as e:
            print(f"❌ Error initializing provider {p_name}: {e}. Trying next...")
            continue

    if initialized_provider:
        return initialized_provider
    else:
        raise RuntimeError("No LLM provider could be initialized from the priority list.")


def _create_ollama_provider(
    model_name: Optional[str],
    custom_config: Optional[Dict[str, Any]],
    llm_config: Dict[str, Any]
) -> OllamaProvider:
    """Create Ollama provider instance"""
    ollama_config = llm_config.get('ollama', {})

    # Determine model
    if model_name is None:
        model_name = ollama_config.get('model', 'jade:v1.0')

    # Build provider config
    provider_config = {
        'base_url': ollama_config.get('base_url', 'http://localhost:11434'),
        'fallback_model': ollama_config.get('fallback', 'jade:v0.9'),
        'timeout': ollama_config.get('timeout', 120)
    }

    # Override with custom config
    if custom_config:
        provider_config.update(custom_config)

    return OllamaProvider(model_name=model_name, config=provider_config)


def _create_openai_provider(
    model_name: Optional[str],
    custom_config: Optional[Dict[str, Any]],
    llm_config: Dict[str, Any]
) -> OpenAIProvider:
    """Create OpenAI provider instance"""
    openai_config = llm_config.get('openai', {})

    # Determine model
    if model_name is None:
        model_name = openai_config.get('model', 'gpt-4-turbo-preview')

    # Build provider config
    provider_config = {}

    # Get API key from config or environment
    api_key_env = openai_config.get('api_key_env', 'OPENAI_API_KEY')
    api_key = openai_config.get('api_key') or os.getenv(api_key_env)
    if api_key:
        provider_config['api_key'] = api_key

    if 'api_base' in openai_config:
        provider_config['api_base'] = openai_config['api_base']

    if 'timeout' in openai_config:
        provider_config['timeout'] = openai_config['timeout']

    # Override with custom config
    if custom_config:
        provider_config.update(custom_config)

    return OpenAIProvider(model_name=model_name, config=provider_config)


def _create_anthropic_provider(
    model_name: Optional[str],
    custom_config: Optional[Dict[str, Any]],
    llm_config: Dict[str, Any]
) -> AnthropicProvider:
    """Create Anthropic provider instance"""
    anthropic_config = llm_config.get('anthropic', {})

    # Determine model
    if model_name is None:
        model_name = anthropic_config.get('model', 'claude-haiku-4-5-20251001')  # Cloud fallback

    # Build provider config
    provider_config = {}

    # Get API key from config or environment
    api_key_env = anthropic_config.get('api_key_env', 'ANTHROPIC_API_KEY')
    api_key = anthropic_config.get('api_key') or os.getenv(api_key_env)
    if api_key:
        provider_config['api_key'] = api_key

    if 'api_base' in anthropic_config:
        provider_config['api_base'] = anthropic_config['api_base']

    if 'timeout' in anthropic_config:
        provider_config['timeout'] = anthropic_config['timeout']

    # Override with custom config
    if custom_config:
        provider_config.update(custom_config)

    return AnthropicProvider(model_name=model_name, config=provider_config)


def _create_gemini_provider(
    model_name: Optional[str],
    custom_config: Optional[Dict[str, Any]],
    llm_config: Dict[str, Any]
) -> GeminiProvider:
    """Create Google Gemini provider instance"""
    gemini_config = llm_config.get('gemini', {})

    # Determine model
    if model_name is None:
        model_name = gemini_config.get('model', 'gemini-pro')

    # Build provider config
    provider_config = {}

    # Get API key from config or environment
    api_key_env = gemini_config.get('api_key_env', 'GOOGLE_API_KEY')
    api_key = gemini_config.get('api_key') or os.getenv(api_key_env)
    if api_key:
        provider_config['api_key'] = api_key

    if 'timeout' in gemini_config:
        provider_config['timeout'] = gemini_config['timeout']

    # Override with custom config
    if custom_config:
        provider_config.update(custom_config)

    return GeminiProvider(model_name=model_name, config=provider_config)


# ============================================================
# SINGLETON PATTERN - ONE LLM PROVIDER FOR THE ENTIRE APP
# ============================================================
_provider_instance: Optional[BaseLLMProvider] = None


def get_llm_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    config_path: Optional[str] = None,
    force_recreate: bool = False
) -> BaseLLMProvider:
    """
    Get singleton LLM provider instance.

    This is the main entry point for JADE to get an LLM provider.

    Args:
        provider_name: Provider type ("ollama", "openai", "anthropic")
        model_name: Model to use
        config: Provider-specific configuration
        config_path: Path to jade_config.yaml
        force_recreate: Force create new instance

    Returns:
        Singleton LLM provider instance

    Example:
        >>> # Use defaults from config (claude-haiku-4-5-20251001 on Anthropic)
        >>> provider = get_llm_provider()
        >>> response = provider.generate("How do I drain a node?")

        >>> # Switch to Ollama
        >>> provider = get_llm_provider(
        ...     provider_name="ollama",
        ...     model_name="jade:v0.9",
        ...     force_recreate=True
        ... )

        >>> # Everywhere in your app uses the same instance
        >>> provider2 = get_llm_provider()
        >>> assert provider is provider2  # True (unless force_recreate)
    """
    global _provider_instance

    if _provider_instance is None or force_recreate:
        if _provider_instance is not None and force_recreate:
            print("🔄 Recreating LLM provider...")
        else:
            print("🔧 Initializing LLM provider (singleton)...")

        _provider_instance = create_provider(
            provider_name=provider_name,
            model_name=model_name,
            config=config,
            config_path=config_path
        )

    return _provider_instance


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================
def switch_provider(
    provider_name: str,
    model_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> BaseLLMProvider:
    """
    Switch to a different LLM provider.

    Args:
        provider_name: New provider ("ollama", "openai", "anthropic")
        model_name: Model to use
        config: Provider-specific configuration

    Returns:
        New LLM provider instance

    Example:
        >>> # Start with Anthropic (default)
        >>> provider = get_llm_provider()

        >>> # Switch to Ollama fallback
        >>> provider = switch_provider("ollama", "jade:v0.9")

        >>> # Switch back to Anthropic
        >>> provider = switch_provider("anthropic", "claude-haiku-4-5-20251001")
    """
    return get_llm_provider(
        provider_name=provider_name,
        model_name=model_name,
        config=config,
        force_recreate=True
    )


def get_provider_info() -> Dict[str, Any]:
    """
    Get current provider information.

    Returns:
        Provider metadata

    Example:
        >>> provider = get_llm_provider()
        >>> info = get_llm_provider()
        >>> print(f"{info['provider']}: {info['model']}")
        'anthropic: claude-haiku-4-5-20251001'
    """
    global _provider_instance

    if _provider_instance is None:
        return {"error": "No provider initialized"}

    return _provider_instance.get_model_info()