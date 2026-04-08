#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para validar configuração do LLM
Uso: python test_llm_config.py
"""

import os
import sys
from dotenv import load_dotenv

# Evita coleta pelo pytest (este arquivo é um script utilitário).
__test__ = False


def _configure_windows_utf8_output() -> None:
    """Configura UTF-8 no terminal Windows sem quebrar o pytest."""
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

# Cores para terminal
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")

def print_warning(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")

def print_info(msg):
    print(f"{BLUE}ℹ{RESET} {msg}")

def check_env_file():
    """Verifica se o arquivo .env existe"""
    if not os.path.exists(".env"):
        print_error("Arquivo .env não encontrado!")
        print_info("Crie o arquivo com base no .env.example")
        return False
    print_success("Arquivo .env encontrado")
    return True

def check_api_keys():
    """Verifica se as API keys estão configuradas"""
    load_dotenv()

    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    if not gemini_key and not openai_key and not groq_key:
        print_error("Nenhuma API key configurada!")
        print_info("Configure GEMINI_API_KEY, OPENAI_API_KEY ou GROQ_API_KEY no .env")
        return False, None

    if gemini_key and gemini_key in ["sua_chave_gemini_aqui", "COLE_SUA_CHAVE_GEMINI_AQUI"]:
        print_error("GEMINI_API_KEY não foi configurada (ainda é placeholder)")
        return False, None

    if openai_key and openai_key in ["sua_chave_aqui", "your_gemini_key_here", "COLE_SUA_NOVA_CHAVE_GEMINI_AQUI"]:
        print_error("OPENAI_API_KEY não foi configurada (ainda é placeholder)")
        return False, None

    if groq_key and groq_key in ["sua_chave_groq_aqui", "your_groq_key_here"]:
        print_error("GROQ_API_KEY não foi configurada (ainda é placeholder)")
        return False, None

    provider = "Gemini (SDK nativo)" if gemini_key else ("OpenAI" if openai_key else "Groq")
    print_success(f"API key configurada ({provider})")
    return True, provider

def check_model_format():
    """Verifica se o formato do modelo está correto"""
    load_dotenv()

    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    if gemini_key:
        model = os.getenv("GEMINI_MODEL")
    elif openai_key:
        model = os.getenv("OPENAI_MODEL")
    else:
        model = os.getenv("GROQ_MODEL")

    if not model:
        print_warning("Modelo não especificado (usará default)")
        return True

    # Verifica formato errado legado do Gemini
    if model.startswith("models/"):
        print_error(f"Formato do modelo incorreto: {model}")
        print_info(f"Remova o prefixo 'models/', use apenas: {model.replace('models/', '')}")
        return False

    print_success(f"Modelo configurado: {model}")
    return True

def check_base_url():
    """Verifica configuração de base URL (apenas OpenAI/Groq)."""
    load_dotenv()

    if os.getenv("GEMINI_API_KEY"):
        print_info("Gemini nativo configurado (OPENAI_BASE_URL não é necessário).")
        return True

    base_url = os.getenv("OPENAI_BASE_URL")
    if not base_url:
        return True  # Groq ou OpenAI padrão

    # Alerta se tentar usar endpoint OpenAI-compat para Gemini
    if "generativelanguage.googleapis.com" in base_url:
        print_warning("OPENAI_BASE_URL aponta para Gemini.")
        print_info("Para maior estabilidade, use GEMINI_API_KEY + GEMINI_MODEL (SDK nativo).")
    else:
        print_success(f"Base URL configurada: {base_url}")

    return True

def test_connection():
    """Testa conexão com o LLM"""
    print_info("Testando conexão com LLM...")

    try:
        from agent.llm import test_llm_connection, LLM_PROVIDER, LLM_MODEL

        print_info(f"Provedor: {LLM_PROVIDER}")
        print_info(f"Modelo: {LLM_MODEL}")

        success = test_llm_connection()

        if success:
            print_success("Conexão com LLM funcionando!")
            return True
        else:
            print_error("Falha ao conectar com LLM")
            return False

    except Exception as e:
        print_error(f"Erro ao testar conexão: {e}")
        print_info("Verifique se todas as dependências estão instaladas: pip install -r requirements.txt")
        return False

def main():
    _configure_windows_utf8_output()

    print("=" * 60)
    print("🔍 Testador de Configuração LLM")
    print("=" * 60)
    print()

    checks = [
        ("Arquivo .env", check_env_file),
        ("API Keys", check_api_keys),
        ("Formato do Modelo", check_model_format),
        ("Base URL", check_base_url),
    ]

    results = []
    for name, check_func in checks:
        print(f"\n📋 Verificando: {name}")
        result = check_func()
        # Se retornar tupla (check_api_keys), pega o primeiro valor
        if isinstance(result, tuple):
            result = result[0]
        results.append(result)

    print("\n" + "=" * 60)

    if all(results):
        print_success("Todas as verificações passaram!")
        print()

        # Teste de conexão
        if test_connection():
            print()
            print_success("Configuração OK! Você pode rodar o servidor:")
            print_info("python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        else:
            print()
            print_error("Configuração OK, mas conexão falhou")
            print_info("Veja TROUBLESHOOTING.md para mais detalhes")
    else:
        print_error("Algumas verificações falharam")
        print_info("Corrija os problemas acima e tente novamente")
        print_info("Consulte TROUBLESHOOTING.md para ajuda detalhada")
        sys.exit(1)

    print()

if __name__ == "__main__":
    main()
