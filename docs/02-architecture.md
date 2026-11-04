# Architektura v0.2

```text
               Użytkownik
                   │
                   ▼
┌──────────────────────────────────────────────┐
│                  Supervisor                  │
│  (Klasyfikacja, Routing, Agregacja w MVP)    │
└──────┬───────────────────────────────┬───────┘
       │                               │
       │ (Zadania / Rekomendacje)       │ (Kontekst / Filtry)
       ▼                               ▼
┌──────────────┐             ┌───────────────────┐
│ Specjaliści  │             │  Memory Manager   │
│ - Coach      │             │  (Algorytmiczny   │
│ - Nutrition  │◄────────────┤   serwis SQL+RAG  │
│ - Physio     │             │   w Pythonie)     │
└──────┬───────┘             └───────────────────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│           Orchestrator / Validator           │
│  (Policy, Schematy JSON, Bramki Safety)      │
└──────────────────────────────────────────────┘
```

## Komponenty

| Komponent | Typ | Odpowiedzialność |
| --- | --- | --- |
| **Supervisor** | Agent LLM | Rozpoznaje domenę/intencję, dobiera agentów, pilnuje bramek bezpieczeństwa i w MVP bezpośrednio agreguje odpowiedź końcową. |
| **Memory Manager** | Serwis w Pythonie (deterministyczny) | Zarządza bazą danych (SQL + wektory), wykonuje zapytania z filtracją uprawnień (Least Privilege) oraz algorytmiczne agregacje (średnie kroczące, sumy makro, luki danych). |
| **Agenci specjaliści** | Agenci LLM | Analizują sprawę wyłącznie w granicach swojej specjalizacji (`Climbing Coach`, `General Nutritionist`, docelowo `Physiotherapist`). |
| **Orchestrator / Validator** | Kod w Pythonie (Pydantic / Asyncio) | Steruje asynchronicznym przepływem zadań (`asyncio.gather()`), weryfikuje schematy JSON (`TASK`, `RECOMMENDATION`, `PROPOSAL`) i egzekwuje reguły `Agent Decision Policy`. |
| **Synthesizer (w MVP: wbudowany w Supervisora)** | Logika Supervisora | W celu redukcji kosztów i opóźnień (latency) w MVP zrezygnowano z osobnego wywołania LLM; Supervisor integruje zatwierdzone rekomendacje w spójną odpowiedź. |

## Przepływ

1. **Klasyfikacja & Routing:** Supervisor analizuje intencję i poziom ryzyka (Direct Response, Single-domain, Multi-domain, Ambiguity).
2. **Kontekst:** Memory Manager zwraca minimalny, przeliczony i przefiltrowany kontekst (zgodnie z macierzą uprawnień).
3. **Analiza dziedzinowa:** Jeden lub wielu specjalistów tworzy ustrukturyzowaną rekomendację (`TASK_RESULT` lub `RECOMMENDATION`).
4. **Walidacja & Bezpieczeństwo:** Orchestrator sprawdza zgodność ze schematami, flagami bezpieczeństwa (`WARNING`, `RESTRICTION`, `CRITICAL ESCALATION`) oraz wykrywa konflikty celów.
5. **Odpowiedź / Propozycja:** Supervisor przedstawia skonsolidowaną odpowiedź dla użytkownika; każda trwała modyfikacja planu wymaga zatwierdzenia obiektu `PROPOSAL`.

Szczegółowe reguły decyzyjne i progi bezpieczeństwa: [docs/04-agent-decision-policy.md](04-agent-decision-policy.md).
