# Climbing Support Team

Wirtualny zespół specjalistów wspierających osobę wspinającą się: trenera wspinaczkowego (`Climbing Coach`), dietetyka ogólnego (`General Nutritionist`) oraz fizjoterapeutę (`Physiotherapist` — w fazie MVP jako bramka ograniczeń medycznych `RESTRICTION`). Całość koordynuje `Supervisor`, który zarządza routingiem adaptacyjnym, Least Privilege Context i w MVP bezpośrednio agreguje odpowiedź końcową.

Projekt zaprojektowany z myślą o lokalnym uruchamianiu (m.in. na pojedynczym GPU RTX 2060 przez Ollama / semafor asynchroniczny) oraz chmurze.

## Cel MVP

- **Przechowywanie danych i kontekstu:** deterministyczny `MemoryManager` (SQLite) z izolacją uprawnień (*Least Privilege Matrix* oraz *Task-Scoped Access*).
- **Trzypoziomowe bezpieczeństwo:** reguły promptów, kontrola w kodzie Orchestratora oraz deterministyczny `PolicyValidator` (blokowanie niedozwolonych ćwiczeń przy urazach, ochrona przed RED-S).
- **Adaptacyjny routing zadań:** bezpośrednie odpowiedzi systemowe (*Direct System Response*), routing jednodomenowy, równoległa dekompozycja oraz sekwencyjny routing adaptacyjny sterowany obiektem `RECOMMENDATION`.
- **Autoryzacja zmian:** każda trwała zmiana w planie wymaga wygenerowania obiektu `PROPOSAL` i jawnej akceptacji użytkownika (`ACCEPTED`).

## Układ katalogów

- `docs/` — decyzje produktowe, specyfikacja architektury (v0.2), roadmapa MVP oraz [Agent Decision Policy v0.2](docs/04-agent-decision-policy.md);
- `agents/` — szczegółowe specyfikacje agentów ([climbing-coach](agents/climbing-coach/SPEC.md), [nutritionist](agents/nutritionist/SPEC.md), [supervisor](agents/supervisor/SPEC.md), [physiotherapist](agents/physiotherapist/SPEC.md));
- `schemas/` — ujednolicone schematy danych (`AgentMessage`, `PROPOSAL`, `RECOMMENDATION`, `EvidenceRecord`);
- `services/` — moduły produkcyjne systemu (`contracts.py` — modele Pydantic, `memory.py` — SQLite MemoryManager, `policy_validator.py` — silnik reguł bezpieczeństwa);
- `tests/` — scenariusze testów jednostkowych i integracyjnych (pokrycie kontraktów, izolacji pamięci i walidatora polityk);
- `knowledge/` — struktura i zasady bazy wiedzy opartej o dowody naukowe (`EvidenceRecord`);
- `data/` — lokalna baza danych SQLite i migracje (wykluczone z repozytorium gita).

## Uruchomienie i testy

Wymagany Python >= 3.11.

```bash
# Instalacja zależności
pip install -r requirements.txt

# Uruchomienie zestawu testów
pytest -v
```

Szczegółowy plan kolejnych etapów: [docs/03-mvp-roadmap.md](docs/03-mvp-roadmap.md).
