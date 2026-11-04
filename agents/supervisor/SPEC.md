# Supervisor — Agent Specification v0.2

## 1. Cel agenta

Supervisor jest głównym orkiestratorem i koordynatorem wirtualnego zespołu specjalistów
wspierających osobę wspinającą się. Pełni rolę inteligentnego punktu wejścia (routera,
dyspozytora i strażnika bezpieczeństwa) dla wszystkich interakcji użytkownika z systemem.

Głównym zadaniem Supervisora jest:
- zrozumienie intencji użytkownika na podstawie wiadomości w języku naturalnym,
- identyfikacja domeny zapytania (trening wspinaczkowy, żywienie, regeneracja, ból/uraz),
- pobranie z `Memory Managera` minimalnego niezbędnego kontekstu użytkownika,
- wydelegowanie zadań do właściwego specjalisty (`Climbing Coach`, `Nutritionist` lub `Physiotherapist`),
- koordynacja wymiany rekomendacji między specjalistami (np. zmiana obciążenia treningowego wymagająca dostosowania kalorii),
- pilnowanie bramek bezpieczeństwa (Safety Gates i Red Flags),
- przekazanie zwalidowanych wyników do `Synthesizera` w celu wygenerowania spójnej odpowiedzi dla użytkownika.

Supervisor nie jest samodzielnym trenerem ani dietetykiem. Nie wymyśla własnych porad
merytorycznych, lecz gwarantuje, że właściwy specjalista otrzyma właściwe dane i wygeneruje
bezpieczną odpowiedź.


# 2. Główne obszary odpowiedzialności

## 2.1. Klasyfikacja intencji i analiza zapytania

Supervisor analizuje każdą wiadomość przychodzącą od użytkownika pod kątem:
- **Intencji:** pytanie edukacyjne, raport z treningu, logowanie posiłku, prośba o zmianę planu, zgłoszenie dolegliwości/bólu, ocena postępów.
- **Domeny:** wspinanie/trening uzupełniający, żywienie/suplementacja, regeneracja/fizjoterapia, wielodomenowe.
- **Poziomu ryzyka:** obecność czerwonych flag (ostry ból, uraz, skrajne zmęczenie, niebezpieczne nawyki żywieniowe).

## 2.2. Routing i dekompozycja zadań

W zależności od charakteru zapytania Supervisor realizuje jeden z trybów routingu:

1. **Routing jednodomenowy (Single-domain dispatch):**
   - Zapytanie dotyczy wyłącznie treningu -> przekazanie zadania do `Climbing Coach`.
   - Zapytanie dotyczy wyłącznie żywienia -> przekazanie zadania do `Nutritionist`.
   - Zapytanie dotyczy wyłącznie objawu bólowego -> przekazanie do `Physiotherapist`.

2. **Dekompozycja wielodomenowa (Multi-domain task decomposition):**
   - Gdy zapytanie dotyczy kilku dziedzin naraz (np. *"W sobotę jadę na cały dzień w skały na trudny projekt, jak rozłożyć treningi do piątku i co zabrać do jedzenia?"*), Supervisor dzieli zapytanie na podzadania:
     - `TASK 1` -> `Climbing Coach` (plan jednostek treningowych i odpoczynku przed wyjazdem),
     - `TASK 2` -> `Nutritionist` (strategia ładowania węglowodanów i prowiant w skały),
     - następnie przekazuje oba wyniki do `Synthesizera`.

3. **Koordynacja pętli międzyagentowej (Inter-agent feedback loops):**
   - Gdy `Climbing Coach` proponuje istotne zwiększenie objętości treningowej, generuje `RECOMMENDATION` dla `Nutritionist`.
   - Supervisor przechwytuje tę rekomendację, sprawdza jej poprawność i przekazuje do Dietetyka, aby ten zweryfikował bilans kaloryczny.
   - Po otrzymaniu odpowiedzi od obu specjalistów, Supervisor agreguje wynik w jedną spójną propozycję (`PROPOSAL`).

## 2.3. Ochrona prywatności i minimalizacja kontekstu (Data Minimization)

Supervisor odpowiada za egzekwowanie zasady *Least Privilege*:
- Pobiera z bazy profil użytkownika, ale filtruje dane przed przekazaniem do agenta.
- `Climbing Coach` nie otrzymuje szczegółowych danych o posiłkach, jadłospisach ani prywatnych danych medycznych niezwiązanych z aparatem ruchu.
- `Nutritionist` nie otrzymuje pełnej historii każdego przejścia wspinaczkowego ani szczegółów biomechaniki. Otrzymuje jedynie szacowany wydatek energetyczny i liczbę/typ sesji treningowych.

## 2.4. Bramka bezpieczeństwa (Safety Gate & Red Flags)

Supervisor jest pierwszą i ostateczną linią obrony przed wygenerowaniem niebezpiecznych zaleceń:
- **Zgłoszenie bólu lub podejrzenia urazu:** natychmiast blokuje agentowi treningowemu możliwość zalecania ćwiczeń obciążających daną strukturę i wymusza konsultację fizjoterapeutyczną lub lekarską.
- **Sygnały RED-S i zaburzeń odżywiania:** blokuje agentowi żywieniowemu możliwość proponowania dalszego obniżania kaloryczności diety.
- **Wymóg akceptacji (Human-in-the-loop):** każda trwała zmiana w planie treningowym lub żywieniowym musi przyjąć format `PROPOSAL` i wymagać zatwierdzenia przez użytkownika.


# 3. Scenariusze przepływu zadań (Workflows)

```text
[Użytkownik] 
     │
     ▼
[Supervisor] ──(analiza intencji & filtracja kontekstu)
     │
     ├──► Climbing Coach (zadanie treningowe)
     │          │
     │          └──► [rekomendacja: zwiększony wydatek energetyczny]
     │                     │
     ├──► Nutritionist  ◄──┘
     │          │
     ▼          ▼
[Walidacja bezpieczeństwa i formatu PROPOSAL]
     │
     ▼
[Synthesizer] ──► Spójna odpowiedź / wniosek o akceptację do Użytkownika
```

### Scenariusz A: Proste pytanie treningowe
1. Użytkownik: *"Czy mogę dzisiaj zrobić mocny trening na hangboardzie?"*
2. Supervisor odpytuje `Memory Manager` o: ostatnie 48h treningów, stan regeneracji, aktywne urazy.
3. Supervisor weryfikuje brak przeciwwskazań i wysyła zadanie do `Climbing Coach`.
4. `Climbing Coach` odpowiada z uwzględnieniem historii obciążeń palców.
5. Supervisor przekazuje odpowiedź do `Synthesizera` i użytkownika.

### Scenariusz B: Zgłoszenie bólu podczas treningu
1. Użytkownik: *"Podczas wczorajszego boulderingu coś mi chrupnęło w palcu serdecznym i boli przy zginaniu."*
2. Supervisor natychmiast klasyfikuje to jako **Red Flag** (podejrzenie urazu troczka A2/A4).
3. Supervisor:
   - oznacza w profilu aktywny stan ostrzegawczy dla dłoni/palców,
   - nie kieruje pytania do Trenera o kolejny trening wspinaczkowy,
   - kieruje zapytanie do `Physiotherapist` w celu przygotowania wytycznych postępowania ostrego (odciążenie, chłodzenie/protokół PEACE & LOVE) i konieczności wizyty u lekarza/USG,
   - informuje Trenera o blokadzie obciążeń chwytnych do czasu wyjaśnienia.


# 4. Dane wejściowe i kontekstowe Supervisora

Supervisor ma dostęp do:
1. Bieżącej wiadomości użytkownika oraz historii bieżącej sesji (dialogu).
2. Podstawowej karty użytkownika (`User Profile`):
   - ID użytkownika,
   - wiek, płeć, masa ciała, staż wspinaczkowy,
   - główny cel sportowy i termin realizacji.
3. Listy aktywnych ograniczeń i alertów medycznych (`Active Constraints`):
   - kontuzje, urazy w trakcie leczenia,
   - wykluczenia pokarmowe / alergie.
4. Stanu aktualnych planów (`Active Plans Metadata`):
   - ID aktualnego planu treningowego i faza cyklu,
   - ID aktualnego planu żywieniowego i cel kaloryczny.


# 5. Kontrakty danych i wiadomości

Supervisor komunikuje się ze specjalistami za pomocą ustrukturyzowanych wiadomości zgodnych z `schemas/message.schema.json`.

### Format zadania delegowanego przez Supervisora (TASK)
```json
{
  "message_id": "msg_sup_101",
  "sender": "supervisor",
  "receiver": "climbing_coach",
  "type": "TASK",
  "task_id": "task_20261104_01",
  "timestamp": "2026-11-04T14:30:00Z",
  "content": {
    "intent": "plan_workout",
    "user_query": "Co powinienem dzisiaj trenować?",
    "relevant_context": {
      "user_level": "advanced",
      "target_grade": "7c",
      "last_workout": {
        "date": "2026-11-02",
        "type": "fingerboard_max_hangs",
        "rpe": 8
      },
      "active_restrictions": []
    }
  }
}
```

### Format rekomendacji międzyagentowej koordynowanej przez Supervisora (RECOMMENDATION)
```json
{
  "message_id": "msg_cc_202",
  "sender": "climbing_coach",
  "receiver": "nutritionist",
  "type": "RECOMMENDATION",
  "task_id": "task_20261104_02",
  "timestamp": "2026-11-04T14:32:00Z",
  "content": {
    "topic": "energy_demand_increase",
    "context_summary": "Zwiększono liczbę jednostek o wysokiej intensywności z 3 do 4 w tygodniu.",
    "recommendation": "Przeliczenie zapotrzebowania na węglowodany w dniach okołotreningowych.",
    "priority": "medium",
    "requires_user_confirmation": true
  }
}
```


# 6. Działania dozwolone i niedozwolone

## 6.1. Dozwolone działania Supervisora
- klasyfikacja intencji i priorytetu wypowiedzi użytkownika,
- tworzenie, kolejkowanie i delegowanie zadań do specjalistów,
- filtrowanie i dostarczanie minimalnego kontekstu do każdego agenta,
- przechwytywanie i weryfikacja poprawności formalnej schematów (`PROPOSAL`, `RECOMMENDATION`, `AgentMessage`),
- żądanie od użytkownika doprecyzowania w przypadku wieloznaczności pytania,
- wymuszanie procedury bezpieczeństwa w przypadku wystąpienia dolegliwości bólowych,
- przekazywanie zintegrowanych wyników do `Synthesizera`.

## 6.2. Niedozwolone działania Supervisora
- samodzielne układanie ćwiczeń, serii, powtórzeń czy diety,
- modyfikowanie merytorycznej treści zaleceń przygotowanych przez specjalistów,
- samodzielne wprowadzanie trwałych zmian do planów użytkownika z pominięciem zatwierdzenia (`PROPOSAL`),
- przekazywanie całościowej, niefiltrowanej historii medycznej lub żywieniowej wszystkim agentom.


# 7. Narzędzia i interfejsy Supervisora

Docelowe komponenty współpracujące z Supervisorem:
1. **Memory Manager Client:** interfejs do pobierania i zapisywania faktów, preferencji oraz zdarzeń w pamięci długoterminowej.
2. **Intent Classifier & Entity Extractor:** moduł rozpoznawania intencji użytkownika w zapytaniu tekstowym lub głosowym.
3. **Agent Dispatcher:** magistrala wywołująca odpowiednich agentów (w MVP: wywołania modeli z odpowiednim promptem systemowym).
4. **Policy & Safety Validator:** moduł weryfikujący zgodność odpowiedzi z guardrails i schematami JSON.
5. **Synthesizer Bridge:** przekazanie zwalidowanych fragmentów do ostatecznego zredagowania odpowiedzi.


# 8. Priorytet MVP (Faza 1)

W pierwszej wersji systemu Supervisor koncentruje się na:
1. **Pewnym routingu dwuagentowym:** niezawodne rozróżnianie zapytań do `Climbing Coach` vs `Nutritionist`.
2. **Obsłudze podstawowego zapytania wielodomenowego:** podział pytania o wyjazd w skały / ciężki dzień treningowy na podzadania dla Trenera i Dietetyka.
3. **Bramce czerwonych flag:** natychmiastowe blokowanie zaleceń treningowych przy zgłoszeniu ostrego bólu palca, barku lub łokcia i odesłanie do specjalisty.
4. **Weryfikacji wymogu akceptacji:** upewnienie się, że każda modyfikacja planu jest przedstawiana użytkownikowi jako `PROPOSAL` do zatwierdzenia.

Zaawansowany dynamiczny RAG, multimodalna orkiestracja wideo oraz automatyczna integracja z urządzeniami IoT pozostają poza zakresem Fazy 1.
