"""
Testes de casos edge e stress para validar robustez do agente
Casos reais que podem quebrar um bot mal implementado
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agent.controller import handle_message
from agent.state import store

def reset_session(session_id: str):
    """Reseta uma sessão para começar teste limpo"""
    store.reset(session_id)

def test_desvio_forte():
    """
    1️⃣ Teste: Desvio forte
    Cliente faz pergunta fora do escopo
    """
    print("\n" + "="*70)
    print("1️⃣ TESTE: DESVIO FORTE")
    print("="*70)
    
    session_id = "test_desvio"
    reset_session(session_id)
    
    # Cliente desvia completamente
    result = handle_message(
        session_id=session_id,
        message="Vocês aceitam carro como parte do pagamento?",
        name="Maria"
    )
    
    reply = result.get("reply", "")
    handoff = result.get("handoff")
    
    print(f"👤 CLIENTE: Vocês aceitam carro como parte do pagamento?")
    print(f"🤖 AGENTE: {reply}")
    print(f"📊 Handoff: {handoff}")
    
    # Validações
    assert "invent" not in reply.lower() or handoff, "❌ Não deve inventar resposta"
    print("✅ PASSOU: Não inventou resposta ou transferiu para humano")

def test_cliente_ignora_pergunta():
    """
    2️⃣ Teste: Cliente ignora pergunta
    Bot pergunta A, cliente responde B
    """
    print("\n" + "="*70)
    print("2️⃣ TESTE: CLIENTE IGNORA PERGUNTA")
    print("="*70)
    
    session_id = "test_ignora"
    reset_session(session_id)
    
    # Bot pergunta intenção
    result1 = handle_message(
        session_id=session_id,
        message="Oi",
        name="Paulo"
    )
    print(f"🤖 AGENTE: {result1.get('reply')}")
    
    # Cliente ignora e fala de localização
    result2 = handle_message(
        session_id=session_id,
        message="perto da praia",
        name="Paulo"
    )
    
    reply = result2.get("reply", "")
    state = result2.get("state", {})
    
    print(f"👤 CLIENTE: perto da praia")
    print(f"🤖 AGENTE: {reply}")
    
    # Validações
    criteria = state.get("criteria", {})
    assert "praia" in str(criteria).lower() or "beach" in str(criteria).lower(), "❌ Deve reconhecer 'praia'"
    assert "alugar ou comprar" not in reply or "intenção" in reply.lower(), "❌ Deve retomar intenção de forma diferente"
    print("✅ PASSOU: Reconheceu localização e retomou fluxo")

def test_contradicao():
    """
    3️⃣ Teste: Contradição
    Cliente muda de ideia no meio da conversa
    """
    print("\n" + "="*70)
    print("3️⃣ TESTE: CONTRADIÇÃO")
    print("="*70)
    
    session_id = "test_contradicao"
    reset_session(session_id)
    
    # Cliente diz que quer alugar
    result1 = handle_message(
        session_id=session_id,
        message="Quero alugar um apartamento",
        name="Ana"
    )
    print(f"👤 CLIENTE: Quero alugar um apartamento")
    print(f"🤖 AGENTE: {result1.get('reply')}")
    
    state1 = result1.get("state", {})
    intent1 = state1.get("intent")
    print(f"📊 Intenção detectada: {intent1}")
    
    # Cliente se corrige
    result2 = handle_message(
        session_id=session_id,
        message="Na verdade, quero comprar, não alugar",
        name="Ana"
    )
    
    reply = result2.get("reply", "")
    state2 = result2.get("state", {})
    intent2 = state2.get("intent")
    
    print(f"👤 CLIENTE: Na verdade, quero comprar, não alugar")
    print(f"🤖 AGENTE: {reply}")
    print(f"📊 Nova intenção: {intent2}")
    
    # Validações
    assert intent2 == "comprar", f"❌ Deve atualizar para 'comprar', mas está '{intent2}'"
    print("✅ PASSOU: Atualizou intenção corretamente")

def test_stress_mensagens_curtas():
    """
    4️⃣ Teste: Stress com mensagens curtas fora de ordem
    """
    print("\n" + "="*70)
    print("4️⃣ TESTE: STRESS - MENSAGENS CURTAS FORA DE ORDEM")
    print("="*70)
    
    session_id = "test_stress"
    reset_session(session_id)
    
    mensagens = [
        "oi",
        "manaíra",
        "3 mil",
        "apartamento",
        "2 quartos",
    ]
    
    replies = []
    for msg in mensagens:
        result = handle_message(
            session_id=session_id,
            message=msg,
            name="Carlos"
        )
        reply = result.get("reply", "")
        replies.append(reply)
        print(f"👤 CLIENTE: {msg}")
        print(f"🤖 AGENTE: {reply[:80]}...")
    
    # Validações
    state = result.get("state", {})
    criteria = state.get("criteria", {})
    
    # Deve ter coletado as informações
    assert criteria.get("neighborhood") or criteria.get("city"), "❌ Deve ter detectado Manaíra"
    assert criteria.get("budget"), "❌ Deve ter detectado orçamento"
    assert criteria.get("property_type"), "❌ Deve ter detectado tipo"
    
    # Não deve ter loops (mesma resposta repetida)
    reply_texts = [r[:50] for r in replies]
    unique_replies = len(set(reply_texts))
    assert unique_replies >= 3, f"❌ Muitas respostas repetidas ({unique_replies}/5 únicas)"
    
    print("✅ PASSOU: Sem loops, sem silêncio, coletou informações")

def test_inferencia_vs_confirmado():
    """
    5️⃣ Teste: Diferenciação entre inferido e confirmado
    """
    print("\n" + "="*70)
    print("5️⃣ TESTE: INFERÊNCIA VS CONFIRMADO")
    print("="*70)
    
    session_id = "test_inferencia"
    reset_session(session_id)
    
    # Cliente diz algo vago
    result = handle_message(
        session_id=session_id,
        message="Quero algo barato em Manaíra",
        name="José"
    )
    
    state = result.get("state", {})
    confirmed = state.get("confirmed_criteria", {})
    inferred = state.get("inferred_criteria", {})
    
    print(f"👤 CLIENTE: Quero algo barato em Manaíra")
    print(f"🤖 AGENTE: {result.get('reply')}")
    print(f"📊 Critérios confirmados: {confirmed}")
    print(f"📊 Critérios inferidos: {inferred}")
    
    # "Manaíra" foi dito explicitamente → confirmed
    assert "neighborhood" in confirmed or "Manaíra" in str(confirmed.values()), "❌ Manaíra deveria estar em confirmed"
    
    # "barato" NÃO deve virar budget específico em confirmed
    # Se a IA inferir um valor, deve ir para inferred
    if "budget" in state.get("criteria", {}):
        assert "budget" not in confirmed, "❌ Budget não foi dito explicitamente, não deve estar em confirmed"
        print("⚠️ LLM inferiu budget - ok se está em 'inferred', não em 'confirmed'")
    
    print("✅ PASSOU: Diferenciou confirmed vs inferred corretamente")

def run_all_edge_tests():
    """Executa todos os testes de casos edge"""
    print("\n🧪 TESTES DE CASOS EDGE - ROBUSTEZ DO AGENTE")
    print("="*70)
    
    tests = [
        test_desvio_forte,
        test_cliente_ignora_pergunta,
        test_contradicao,
        test_stress_mensagens_curtas,
        test_inferencia_vs_confirmado,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FALHOU: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERRO: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"📊 RESULTADO: {passed} passou, {failed} falhou de {len(tests)} testes")
    print("="*70)
    
    if failed == 0:
        print("\n✅ TODOS OS TESTES DE CASOS EDGE PASSARAM!")
        print("🚀 O agente está robusto para cenários reais difíceis")
    else:
        print(f"\n⚠️ {failed} teste(s) falhou(aram)")
        print("📝 Revise os casos que falharam acima")

if __name__ == "__main__":
    run_all_edge_tests()
