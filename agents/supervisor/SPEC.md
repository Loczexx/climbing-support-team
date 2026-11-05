# Supervisor — Agent Specification v0.2

## 1. Cel agenta

Supervisor jest centralnym agentem koordynującym system wieloagentowy (Multi-Agent System). Odpowiada za zarządzanie interakcjami z użytkownikiem, rozpoznawanie intencji, kierowanie zadań do odpowiednich wyspecjalizowanych agentów (`Climbing Coach`, `General Nutritionist` oraz przyszłych specjalistów), nadzorowanie komunikacji międzyagentowej oraz dbanie o spójność i bezpieczeństwo całego systemu.

Supervisor wykorzystuje:
- intencję użytkownika,
- globalny profil i główne cele użytkownika,
- statusy aktywnych agentów i ich ostatnie wyniki,
- podsumowania oraz istotne informacje udostępniane przez `Memory Manager`,
- aktywne ograniczenia i flagi bezpieczeństwa,
- propozycje zmian (`PROPOSALS`),
- reguły systemowe i polityki decyzyjne (`Agent Decision Policy`).

Supervisor nie zastępuje ekspertów dziedzinowych. Nie układa samodzielnie specjalistycznych planów treningowych ani dietetycznych. Jego zadaniem jest określenie, kto i kiedy powinien zająć się problemem, jakie informacje będą potrzebne oraz jak skoordynować i przedstawić wyniki użytkownikowi.

Supervisor nie jest również odpowiedzialny za techniczne wykonywanie zadań, zarządzanie bazą danych ani bezpośrednie zarządzanie pamięcią. Te obowiązki należą do odpowiednich komponentów programowych (`Orchestrator`, `Memory Manager`).


# 2. Zakres odpowiedzialności

## 2.1. Routing i dekompozycja zadań (Intent Recognition & Task Decomposition)

Supervisor analizuje wiadomości użytkownika (intencję, domenę oraz poziom ryzyka) i realizuje jeden z trybów obsługi:

1. **Bezpośrednia obsługa systemowa (Direct System Response):**
   - Proste zapytania o stan systemu, aktywne cele, dostępnych agentów lub oczekujące propozycje (`PROPOSALS`) Supervisor obsługuje samodzielnie na podstawie dostępnego kontekstu, bez uruchamiania modeli specjalistów.
2. **Routing jednodomenowy (Single-domain dispatch):**
   - Zapytanie dotyczy wyłącznie treningu → `Climbing Coach`.
   - Zapytanie dotyczy wyłącznie żywienia → `General Nutritionist`.
   - Zapytanie dotyczy wyłącznie objawu bólowego/rehabilitacji → procedura `RESTRICTION` i skierowanie do opieki medycznej (w MVP).
3. **Dekompozycja wielodomenowa (Parallel Multi-Domain):**
   - Gdy zapytanie dotyczy kilku dziedzin naraz od początku (np. przygotowanie treningowe i żywieniowe pod weekendowy wyjazd w skały), Orchestrator uruchamia zadania dla obu specjalistów (`TASK 1` dla `Climbing Coach`, `TASK 2` dla `General Nutritionist`), a po ich wykonaniu Supervisor agreguje wyniki w jedną spójną odpowiedź.
4. **Routing adaptacyjny sekwencyjny (Adaptive Sequential Routing):**
   - W przypadku problemów wieloczynnikowych o nieznanej przyczynie (np. *„Od 2 tygodni nie mam siły na treningach”*) Orchestrator uruchamia najpierw głównego specjalistę (`Climbing Coach`). Drugi specjalista (`General Nutritionist`) jest uruchamiany sekwencyjnie **tylko wtedy**, gdy pierwszy agent dołączy obiekt `RECOMMENDATION` wskazujący na potrzebę weryfikacji żywieniowej. Eliminuje to zbędne wywołania drugiego modelu na RTX 2060, gdy przyczyna leży wyłącznie w przeciążeniu treningowym.
5. **Obsługa niejednoznacznych zapytań (Ambiguity Resolution):**
   - Gdy intencja nie jest jasna lub brakuje kluczowych danych, Supervisor zadaje użytkownikowi krótkie pytanie doprecyzowujące przed uruchomieniem specjalistów.

## 2.2. Koordynacja międzyagentowa (Inter-Agent Coordination)

Supervisor odpowiada za nadzorowanie pętli komunikacji między specjalistami:
- przekazuje ustrukturyzowane rekomendacje (`RECOMMENDATION`) między agentami (np. od `Climbing Coacha` do `General Nutritionista` po zwiększeniu objętości treningowej),
- sprawdza, czy rekomendacja wymaga konsultacji z kolejnym specjalistą,
- monitoruje status przekazanych zadań,
- kontroluje, czy rekomendacje uwzględniają aktualne cele i ograniczenia użytkownika,
- zbiera wyniki pracy kilku agentów i przygotowuje spójną odpowiedź końcową.

Supervisor nie uznaje automatycznie rekomendacji jednego agenta za niepodważalny fakt — agent odbierający rekomendację weryfikuje ją względem własnej bazy wiedzy i danych.

## 2.3. Rozwiązywanie konfliktów (Conflict Resolution)

Supervisor odpowiada za wykrywanie sprzeczności między:
- celami użytkownika,
- rekomendacjami różnych agentów (np. `General Nutritionist` planuje wyraźny deficyt kaloryczny, podczas gdy `Climbing Coach` rozpoczyna ciężki blok siły palców),
- aktualnymi planami a aktywnymi ograniczeniami treningowymi lub żywieniowymi,
- nowymi propozycjami a wcześniej zaakceptowanymi decyzjami.

Procedura postępowania przy konflikcie:
1. Wykrycie potencjalnego konfliktu (`GOAL_CONFLICT`).
2. Określenie, których agentów należy ponownie skonsultować, i przekazanie im informacji o sprzeczności.
3. Zebranie od specjalistów oceny konsekwencji oraz alternatywnych wariantów.
4. Przygotowanie spójnego podsumowania dla użytkownika.
5. Przedstawienie użytkownikowi wariantów w formie `PROPOSAL` lub prośby o wskazanie priorytetowego celu.

Supervisor koordynuje rozwiązanie konfliktu, ale nie zastępuje specjalistów w ocenie merytorycznej.

## 2.4. Zarządzanie kontekstem (Context Provision & Least Privilege)

Supervisor określa, jakich danych potrzebuje dany agent do wykonania konkretnego zadania, stosując zasadę najmniejszego uprzywilejowania (*Least Privilege*):
- zleca przekazanie wyłącznie informacji niezbędnych do realizacji bieżącego zadania,
- chroni przed udostępnianiem pełnej historii medycznej, psychologicznej czy farmakologicznej,
- zapobiega przekazywaniu surowych dzienników posiłków do `Climbing Coacha` oraz szczegółowych logów każdej serii wspinaczkowej do `General Nutritionista`.

Podział odpowiedzialności:
- **Supervisor** — określa, jakiego zakresu informacji potrzebuje dany agent.
- **Memory Manager** — deterministyczny serwis programowy w Pythonie (SQL + algorytmy agregujące), który pobiera, filtruje i udostępnia odpowiednie dane.
- **Specialist Agent** — wykorzystuje otrzymane dane do analizy dziedzinowej.

## 2.5. Nadzór nad bezpieczeństwem (Safety & Guardrails)

Supervisor nadzoruje przestrzeganie globalnych zasad bezpieczeństwa systemu. Nie diagnozuje chorób ani urazów i nie zastępuje lekarza, fizjoterapeuty ani dietetyka klinicznego.

Stosuje trzy poziomy reakcji bezpieczeństwa:

- **WARNING (Ostrzeżenie):**
  Sytuacja wymagająca zwiększonej ostrożności w analizie specjalisty, ale nieblokująca standardowego działania systemu (np. pogorszenie snu, narastające zmęczenie, pojedynczy niepełny dzień żywieniowy).
- **RESTRICTION (Ograniczenie):**
  Sytuacja wymagająca wstrzymania określonych działań w danej domenie do czasu wyjaśnienia problemu (np. zgłoszony ból palca lub łokcia wstrzymuje zalecanie obciążeń dla tej struktury przez `Climbing Coacha`; sygnały niebezpiecznie niskiej dostępności energii wstrzymują propozycje pogłębiania deficytu przez `General Nutritionista`). Ograniczenie dotyczy konkretnych działań, a nie blokady całego systemu.
- **CRITICAL ESCALATION (Eskalacja krytyczna):**
  Sytuacja wymagająca natychmiastowego przerwania standardowego przepływu (np. ostry uraz ze słyszalnym trzaskiem i utratą funkcji, skrajne objawy wyniszczenia/RED-S). Supervisor wstrzymuje potencjalnie ryzykowne działania systemowe, jasno komunikuje wykryte zagrożenie i zaleca pilny kontakt z lekarzem lub odpowiednim specjalistą poza systemem.


# 3. Przykładowe zadania i zapytania

## 3.1. Routing i zapytania ogólne
- *„Jak powinien wyglądać mój tydzień treningowy?”* → `Climbing Coach`.
- *„Ile kalorii powinienem spożywać?”* → `General Nutritionist`.
- *„Chcę schudnąć 3 kg przed wyjazdem w skały w maju i poprawić wytrzymałość.”* → dekompozycja zadań dla `Climbing Coacha` i `General Nutritionista`.
- *„Czuję się dzisiaj bardzo zmęczony. Co powinienem zrobić?”* → analiza zależna od kontekstu (lub pytanie doprecyzowujące), potencjalnie `Climbing Coach` i `General Nutritionist`.
- *„Jakie mam aktualne cele i jakie propozycje czekają na zatwierdzenie?”* → bezpośrednia odpowiedź `Supervisora` (Direct System Response).

## 3.2. Zarządzanie konfliktami
- Użytkownik oczekuje szybkiej redukcji masy ciała podczas rozpoczynania intensywnego cyklu siłowego.
- Nowa propozycja zmiany planu koliduje z aktywnym ograniczeniem rehabilitacyjnym.

## 3.3. Bezpieczeństwo
- Użytkownik zgłasza ostry ból podczas wspinania → `RESTRICTION` / `CRITICAL ESCALATION`, blokada obciążeń bolesnej struktury, skierowanie do lekarza.
- `General Nutritionist` zgłasza sygnały przewlekle niskiej dostępności energii (ryzyko RED-S) → blokada dalszej redukcji, koordynacja z `Climbing Coachem` w celu obniżenia objętości.


# 4. Dane dostępne dla Supervisora

Supervisor operuje na zwięzłym zestawie metadanych i podsumowań, co ogranicza zużycie tokenów i chroni prywatność.

## 4.1. Globalny profil użytkownika
- identyfikator użytkownika (`user_id`),
- główne cele i terminy ich realizacji,
- aktywne specjalizacje i preferencje komunikacji,
- aktywne ograniczenia globalne (kontuzje, wykluczenia dietetyczne).

## 4.2. Status systemu
- lista dostępnych agentów,
- statusy aktywnych zadań (`TASKS`),
- statusy oczekujących propozycji (`PROPOSALS`),
- aktywne flagi bezpieczeństwa (`WARNING`, `RESTRICTION`, `CRITICAL ESCALATION`),
- istotne błędy i ograniczenia systemowe.

## 4.3. Podsumowania użytkownika
- podsumowania tygodniowe i miesięczne z `Memory Managera`,
- metadane aktualnych planów (np. faza mikrocyklu treningowego, aktualny cel kaloryczny).

## 4.4. Ograniczenia dostępu
Supervisor nie przetwarza domyślnie:
- surowych dzienników posiłków,
- szczegółowych logów pojedynczych serii treningowych i wstawek,
- pełnej historii medycznej, farmakologicznej ani prywatnych danych psychologicznych.


# 5. Działania dozwolone

Supervisor może:
- klasyfikować intencje użytkownika i priorytetyzować zadania,
- samodzielnie odpowiadać na proste zapytania systemowe (cele, statusy, dostępni agenci),
- kierować zadania do specjalistów i uruchamiać konsultacje wieloagentowe,
- określać wymagany kontekst dla agentów i zlecać jego pobranie przez `Memory Manager`,
- przekazywać rekomendacje (`RECOMMENDATION`) między agentami,
- wykrywać konflikty między rekomendacjami i celami,
- inicjować procedury bezpieczeństwa (`WARNING`, `RESTRICTION`, `CRITICAL ESCALATION`),
- agregować wyniki wielu agentów w jedną spójną odpowiedź dla użytkownika (w MVP pełcząc bezpośrednio funkcję syntezy),
- zarządzać cyklem życia `PROPOSAL`,
- zapisywać metadane systemowe i logi decyzyjne przez `Memory Manager`.


# 6. Zarządzanie propozycjami (PROPOSAL Management)

Supervisor nadzoruje cykl życia propozycji zmian generowanych przez specjalistów.

## 6.1. Obsługiwane statusy
- `CREATED` — propozycja została utworzona przez specjalistę.
- `PENDING_REVIEW` — przedstawiona użytkownikowi, oczekuje na decyzję.
- `ACCEPTED` — użytkownik zaakceptował propozycję.
- `REJECTED` — użytkownik odrzucił propozycję.
- `MODIFIED` — użytkownik poprosił o modyfikację warunków.
- `APPLIED` — zaakceptowana zmiana została zapisana w planie.
- `CANCELLED` — propozycja została anulowana lub zdezaktualizowana przez nowe dane.

## 6.2. Obowiązki Supervisora
- prezentowanie propozycji użytkownikowi wraz z uzasadnieniem, celem i ryzykiem przygotowanym przez specjalistę,
- umożliwianie niezależnej akceptacji, odrzucenia lub modyfikacji poszczególnych zmian (nawet jeśli zostały zaprezentowane w jednym podsumowaniu od kilku agentów),
- pilnowanie, aby ta sama zmiana nie została zastosowana dwukrotnie,
- unieważnianie (`CANCELLED`) oczekujących propozycji, jeśli w międzyczasie pojawiły się nowe, sprzeczne dane (np. zgłoszenie kontuzji),
- zlecanie zapisu decyzji użytkownika (w tym opcjonalnego powodu odrzucenia) w `Memory Managerze`.


# 7. Działania wymagające zatwierdzenia użytkownika

Supervisor nie może samodzielnie (bez procesu `PROPOSAL` i zgody użytkownika):
- zmieniać głównych celów użytkownika,
- modyfikować planów treningowych ani żywieniowych,
- wdrażać skonsolidowanych propozycji wielu agentów,
- rozstrzygać konfliktów dotyczących osobistych priorytetów użytkownika.


# 8. Zarządzanie zadaniami (Task Management)

Zadania delegowane do specjalistów są koordynowane programowo przez asynchroniczny runtime w Pythonie (`asyncio`).

## 8.1. Statusy zadań
- `PENDING` — zadanie oczekuje w kolejce / pętli zdarzeń.
- `RUNNING` — zadanie jest przetwarzane przez model specjalisty.
- `COMPLETED` — zadanie zakończone poprawnym wynikiem.
- `FAILED` — zadanie zakończone błędem walidacji lub wykonania.
- `CANCELLED` — zadanie anulowane.
- `TIMEOUT` — przekroczono dozwolony czas oczekiwania na odpowiedź.

## 8.2. Koordynacja zadań i współbieżność
Supervisor określa, które zadania mogą biec równolegle (np. dekompozycja wielodomenowa za pomocą `asyncio.gather()`), a które sekwencyjnie (np. przekazanie `RECOMMENDATION` od Trenera do Dietetyka). Na środowisku lokalnym (GPU RTX 2060) wywołania modeli są owinięte w semafor współbieżności (`asyncio.Semaphore(1)`), aby zapobiec przeciążeniu VRAM. Jeżeli jeden z agentów zwróci błąd lub przekroczy czas (`TIMEOUT`), Supervisor nie blokuje całej odpowiedzi, lecz przedstawia użytkownikowi wynik częściowy wraz z jawną informacją o brakującym elemencie.


# 9. Obsługa błędów i brakujących danych

## 9.1. Niekompletne dane
Jeżeli specjalista zgłasza brak danych niezbędnych do analizy (np. niepełny dziennik posiłków lub brak informacji o sprzęcie), Supervisor:
1. sprawdza przez `Memory Manager`, czy dane są dostępne w zasobach,
2. jeśli ich brakuje — prosi użytkownika o doprecyzowanie lub nakazuje specjaliście wykonanie analizy częściowej z odpowiednim oznaczeniem niepewności.

## 9.2. Błędy agentów
W przypadku niepoprawnej struktury odpowiedzi lub błędu wykonania `Orchestrator` ponawia próbę zgodnie z limitem, a po jego wyczerpaniu Supervisor informuje użytkownika o ograniczeniu, nigdy nie prezentując uszkodzonych lub zmyślonych danych jako poprawnej rekomendacji.


# 10. Współpraca z komponentami technicznymi

1. **Orchestrator (Deterministyczny kod w Pythonie):**
   Odpowiada za techniczną realizację przepływu pracy: wywoływanie modeli specjalistów, przekazywanie wiadomości, współbieżność asynchroniczną (`asyncio`), kontrolę timeoutów, ponowienia (retries) oraz twardą walidację schematów JSON (Pydantic). Nie wymaga osobnego modelu LLM.
2. **Memory Manager (Deterministyczny moduł bazodanowo-algorytmiczny w Pythonie):**
   NIE jest modelem konwersacyjnym LLM. To czysty serwis programowy zarządzający relacyjną bazą danych (SQLite) oraz bazą wektorową. Odpowiada za:
   - filtrowanie kontekstu zgodnie z Least Privilege Matrix (np. `get_coach_context()`),
   - obliczenia statystyczne i agregacje (średnie kroczące masy 7/14 dni, sumowanie makro, Missing Data Gate),
   - wyszukiwanie dowodów naukowych w wektorach RAG (wyliczanych na CPU).
   Opcjonalne małe wywołanie LLM w tle może występować wyłącznie poza główną ścieżką zapytań (np. okresowa kompresja historii do podsumowania miesięcznego).
3. **Brak osobnego modelu Synthesizera w MVP:**
   W celu eliminacji zbędnych kosztów i opóźnień (latency) zrezygnowano z osobnego wywołania LLM dla Synthesizera. Supervisor sam agreguje zwalidowane odpowiedzi od agentów specjalistów w jedną spójną wiadomość dla użytkownika.
4. **Specialist Agents:**
   `Climbing Coach`, `General Nutritionist`, a docelowo także `Physiotherapist` oraz `Sport Psychologist`. Odpowiadają wyłącznie za analizę merytoryczną w swoich domenach.


# 11. Komunikacja międzyagentowa (Inter-Agent Communication)

Wszystkie komunikaty wymieniane w systemie podlegają walidacji względem schematów JSON i należą do czterech typów:

### 11.1. Zadanie delegowane przez Supervisora (`TASK`)
```json
{
  "message_id": "msg_sup_101",
  "sender": "supervisor",
  "receiver": "climbing_coach",
  "user_id": "usr_12345",
  "type": "TASK",
  "task_id": "task_20261104_01",
  "timestamp": "2026-11-04T14:30:00Z",
  "content": {
    "intent": "evaluate_workout_readiness",
    "user_query": "Czy mogę dzisiaj zrobić mocny trening na hangboardzie?",
    "relevant_context": {
      "target_goal": "Lead 7c RP",
      "last_climbing_sessions_summary": "2026-11-02: Bouldering (RPE 8, 2h)",
      "skin_condition": "good",
      "active_restrictions": []
    }
  }
}
```

### 11.2. Rekomendacja międzyagentowa (`RECOMMENDATION`)
```json
{
  "message_id": "msg_rec_201",
  "sender": "climbing_coach",
  "receiver": "nutritionist",
  "user_id": "usr_12345",
  "type": "RECOMMENDATION",
  "task_id": "task_20261104_02",
  "timestamp": "2026-11-04T14:32:00Z",
  "content": {
    "topic": "energy_expenditure_increase",
    "context_summary": "Zwiększono częstotliwość jednostek o wysokiej intensywności z 3 do 4 w tygodniu.",
    "recommendation": "Dostosowanie podaży energii i węglowodanów w dniach okołotreningowych.",
    "priority": "medium",
    "requires_user_confirmation": true
  }
}
```

### 11.3. Propozycja trwałej modyfikacji planu (`PROPOSAL`)
```json
{
  "proposal_id": "prop_20261104_01",
  "domain": "training",
  "status": "PENDING_REVIEW",
  "current_state": {
    "weekly_sessions": 3,
    "focus": "hypertrophy"
  },
  "proposed_change": {
    "weekly_sessions": 4,
    "focus": "finger_strength_max_hangs"
  },
  "reason": "Zakończenie bloku adaptacji anatomicznej, przejście do fazy siły maksymalnej przed projektem RP.",
  "evidence": ["Schoenfeld 2020", "Bechtel 2019"],
  "risk": "Zwiększone obciążenie aparatu więzadłowo-ścięgnistego palców; wymagany deload po 4 tygodniach.",
  "requires_user_confirmation": true
}
```

### 11.4. Komunikat odpowiedzi i wynik zadania (`MESSAGE` / `TASK_RESULT`)
```json
{
  "message_id": "msg_resp_301",
  "sender": "climbing_coach",
  "receiver": "supervisor",
  "user_id": "usr_12345",
  "type": "TASK_RESULT",
  "task_id": "task_20261104_01",
  "timestamp": "2026-11-04T14:30:45Z",
  "content": {
    "status": "SUCCESS",
    "analysis": "Palce są zregenerowane po 48h przerwy od sesji boulderingowej.",
    "recommendation": "Możesz wykonać sesję Max Hangs (5x10s przy 85% masy maks.), z 3-minutową przerwą.",
    "confidence": 0.9,
    "evidence_ids": ["ev_hangboard_01"]
  }
}
```


# 12. Priorytet MVP (Faza 1)

W pierwszej wersji systemu (uruchomienie lokalne na RTX 2060 / Ollama) implementacja Supervisora skupia się na:
1. **Niezawodnym routingu 2-agentowym:** precyzyjna klasyfikacja intencji użytkownika pomiędzy `Climbing Coach` a `General Nutritionist`.
2. **Obsłudze Direct System Response:** bezpośrednie zwracanie celów i statusów z bazy SQLite bez narzutu zapytań do modeli specjalistów.
3. **Dekompozycji zapytań wielodomenowych:** obsługa łączonych zapytań z asynchronicznym wywołaniem agentów kontrolowanym semaforem GPU (`asyncio.Semaphore(1)`).
4. **Egzekwowaniu bramek bezpieczeństwa:** natychmiastowe wdrożenie `RESTRICTION` lub `CRITICAL ESCALATION` przy zgłoszeniu bólu aparatu ruchu lub skrajnego wycieńczenia.
5. **Generowaniu i walidacji `PROPOSAL`:** pełna kontrola nad cyklem życia propozycji zmian w planach z wymogiem jawnej akceptacji użytkownika.
6. **Agregacji odpowiedzi bez osobnego Synthesizera:** zwięzłe i spójne łączenie wyników od specjalistów w jedną wiadomość dla użytkownika.
