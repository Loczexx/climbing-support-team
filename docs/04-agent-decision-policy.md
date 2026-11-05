# Agent Decision Policy — System Rules & Thresholds v0.2

## 1. Purpose & Enforcement (Cel i egzekwowanie reguł)

Dokument definiuje wspólne reguły decyzyjne, macierz uprawnień, zasady routingu adaptacyjnego, progi bezpieczeństwa oraz cykl życia propozycji (`PROPOSAL`) dla całego ekosystemu (`Supervisor`, `Climbing Coach`, `General Nutritionist` oraz przyszłych specjalistów).

Egzekwowanie reguł odbywa się na trzech warstwach:
1. **Agent Instructions (Prompty systemowe):** interpretacja merytoryczna, ocena kontekstu i formułowanie zaleceń.
2. **Orchestrator & Memory Manager (Komponenty programowe):** kontrola uprawnień odczytu/zapisu, filtrowanie zapytań SQL/RAG, kontrola timeoutów i zarządzanie przepływem zadań.
3. **Policy Validator (Deterministyczna walidacja wyników):** zestaw funkcji programowych sprawdzających przed zwróceniem odpowiedzi, czy wygenerowany wynik lub `PROPOSAL` nie narusza aktywnych ograniczeń (`RESTRICTION`), schematów JSON oraz twardych blokad bezpieczeństwa.


## 2. Least Privilege Matrix (Domyślna macierz uprawnień)

Uprawnienia są podzielone na odczyt (`READ`) oraz zapis/modyfikację (`WRITE`). Zapis trwałych zmian w planach zawsze wymaga autoryzacji użytkownika (`PROPOSAL`).

| Kategoria danych | Supervisor | Climbing Coach | General Nutritionist |
| :--- | :--- | :--- | :--- |
| **Profil podstawowy** (wiek, wzrost, płeć) | `READ` (niezbędne pola) | `READ` | `READ` |
| **Główne cele i terminy** | `READ` / `WRITE` (po `PROPOSAL`) | `READ` / `WRITE` (cele treningowe po `PROPOSAL`) | `READ` / `WRITE` (cele wagowe/żywieniowe po `PROPOSAL`) |
| **Flagi bezpieczeństwa** (`WARNING`, `RESTRICTION`, `CRITICAL`) | `READ` / `WRITE` | `READ` (treningowe) / `WRITE` (zgłoszenie flagi) | `READ` (żywieniowe) / `WRITE` (zgłoszenie flagi) |
| **Historia treningów i wspinania** | `READ` (tylko podsumowania) | `READ` / `WRITE` (pełny dostęp) | `READ` (tylko podsumowania obciążenia: liczba, typ, czas, ogólna intensywność, wyjazdy) |
| **Standaryzowane testy (`Assessments`)** | `READ` (wybrane podsumowania) | `READ` / `WRITE` (pełny dostęp z protokołem) | Brak dostępu |
| **Surowe dzienniki posiłków** | Brak dostępu | Brak dostępu | `READ` / `WRITE` (pełny dostęp) |
| **Masa ciała** | `READ` (podsumowania trendu) | `READ` (aktualna masa i trend, jeśli istotne dla wyniku) | `READ` / `WRITE` (pełny dostęp) |
| **Skład ciała (BF%)** | `READ` (podsumowania, jeśli potrzebne) | Brak domyślnego dostępu | `READ` / `WRITE` (pełne dane wraz z metodą pomiaru) |
| **Ograniczenia treningowe i urazy** | `READ` (flagi operacyjne) | `READ` / `WRITE` (pełny odczyt ograniczeń aparatu ruchu) | Brak domyślnego dostępu (dostęp przez *Task-scoped access*) |
| **Ograniczenia dietetyczne i interakcje lek–żywność** | `READ` (flagi operacyjne) | Brak domyślnego dostępu (dostęp przez *Task-scoped access*) | `READ` / `WRITE` (pełny odczyt wykluczeń i istotnych interakcji) |
| **Pełna historia medyczna i psychologiczna** | Brak dostępu | Brak dostępu | Brak dostępu |


## 3. Dynamic Access Control (Tymczasowe rozszerzanie dostępu — Task-Scoped Access)

Domyślna macierz uprawnień może zostać tymczasowo rozszerzona wyłącznie na czas wykonywania konkretnego zadania (`task_id`), jeżeli wymaga tego cel zapytania (np. użytkownik prosi `General Nutritionista` o dietę wspierającą gojenie zerwanego troczka).

### Zasady działania:
1. **Brak samodzielnej eskalacji:** Specjalista nie może sam pobrać danych spoza swojej domeny.
2. **Autoryzacja przez Supervisora lub Orchestrator:** Rozszerzenie zakresu (`granted_scopes`) jest nadawane przez `Supervisora` przy tworzeniu zadania (`TASK`) lub zatwierdzane po zgłoszeniu zapotrzebowania (`required_data` w obiekcie `RECOMMENDATION`).
3. **Minimalny wycinek:** Rozszerzenie udostępnia wyłącznie ustrukturyzowany wycinek danych (np. obiekt aktywnego ograniczenia urazowego), a nigdy pełną historię innej domeny.
4. **Automatyczne wygasanie i audyt:** Uprawnienie wygasa natychmiast po zmianie statusu zadania na `COMPLETED` / `FAILED`, a operacja zostaje zapisana w logach.

```json
{
  "access_grant_id": "grant_20261104_01",
  "requesting_agent": "general_nutritionist",
  "task_id": "task_20261104_05",
  "data_scope": ["active_injury_restrictions_summary"],
  "purpose": "recovery_nutrition_adjustment",
  "approved_by": "supervisor",
  "expires_after_task": true
}
```


## 4. Routing & Decomposition (Routing adaptacyjny i dekompozycja)

Supervisor oraz Orchestrator dobierają tryb wywołania agentów w zależności od stopnia złożoności i jednoznaczności problemu:

| Sytuacja | Tryb routingu | Opis działania |
| :--- | :--- | :--- |
| **Zapytanie o status systemu, cele, oczekujące PROPOSALS** | `Direct System Response` | Supervisor odpowiada bezpośrednio z metadanych, bez uruchamiania modeli specjalistów. |
| **Problem dotyczy głównie jednej domeny i nie zmienia planu innego specjalisty** | `Single-Domain Dispatch` | Zadanie trafia wyłącznie do jednego specjalisty (`Climbing Coach` lub `General Nutritionist`). |
| **Problem jednoznacznie obejmuje wiele domen od samego początku** (np. plan treningowy i żywieniowy na wyjazd w skały) | `Parallel Multi-Domain` | Orchestrator uruchamia zadania dla obu specjalistów (w chmurze równolegle, lokalnie na pojedynczym GPU w kolejce semafora). |
| **Problem wieloczynnikowy o nieznanej przyczynie** (np. „Od 2 tygodni nie mam siły”) lub wynik pierwszego agenta wymaga konsultacji | `Adaptive Sequential Routing` | Uruchamiany jest najpierw główny specjalista (np. `Climbing Coach`). Drugi specjalista (`General Nutritionist`) jest uruchamiany sekwencyjnie tylko wtedy, gdy pierwszy agent wygeneruje obiekt `RECOMMENDATION` lub wskaże na potrzebę weryfikacji drugiej domeny. |
| **Brak kluczowych informacji do przypisania domeny lub oceny bezpieczeństwa** | `Ambiguity Resolution` | Supervisor zadaje użytkownikowi możliwie najmniejszą liczbę pytań doprecyzowujących przed uruchomieniem specjalistów. |


## 5. Material Changes & Deviations (Istotne zmiany i odstępstwa od planu)

System rozróżnia bieżące porady od zmian strukturalnych:

### 5.1. Istotna zmiana planu (Material Change — wymaga PROPOSAL)
- **Trening:** nowy program treningowy, zmiana liczby dni treningowych w tygodniu, zmiana priorytetu cyklu (np. z wytrzymałości na siłę palców), zmiana obciążeń/objętości w głównych ćwiczeniach, dodanie nieplanowanego deloadu, przebudowa reszty tygodnia po odstępstwie.
- **Żywienie:** nowy cel kaloryczny, zmiana docelowego rozkładu makroskładników, zmiana głównego celu wagowego (redukcja / utrzymanie / masa), zmiana stałego szablonu posiłków.

### 5.2. Istotne odstępstwo od planu (Significant Deviation — wyzwala ocenę rekalibracji)
- **Trening:** wykonanie nieplanowanej, ciężkiej sesji (np. dzień w skałach zamiast dnia odpoczynku), pominięcie kluczowej jednostki w mikrocyklu, nagły skok RPE lub pogorszenie stanu skóry uniemożliwiające realizację kolejnego treningu.
- **Żywienie:** wielodniowe, potwierdzone odchylenie od docelowej podaży energii (po odfiltrowaniu dni niekompletnych) lub zmiana obciążenia treningowego zgłoszona przez `Climbing Coacha`.


## 6. PROPOSAL Authorization (Autoryzacja zmian przez użytkownika)

1. Żadna istotna zmiana planu lub celu nie może wejść w życie (`APPLIED`) bez przejścia przez status `PENDING_REVIEW` oraz wyraźnej decyzji użytkownika (`ACCEPTED`).
2. Obiekt `PROPOSAL` musi zawierać: stan obecny, proponowaną zmianę, uzasadnienie, cel, wykorzystane źródła wiedzy (`EvidenceRecord`), poziom pewności oraz potencjalne ryzyko.
3. W przypadku skonsolidowanej prezentacji propozycji od kilku agentów użytkownik ma prawo zaakceptować wybrane propozycje i odrzucić pozostałe, o ile nie są ze sobą nierozerwalnie powiązane ze względów bezpieczeństwa.
4. Policy Validator blokuje ponowne wdrożenie (`APPLIED`) propozycji, która została już raz zastosowana lub unieważniona (`CANCELLED`).


## 7. Conflict Resolution (Rozwiązywanie konfliktów między agentami)

Gdy cele lub rekomendacje specjalistów są ze sobą sprzeczne (np. głęboki deficyt kaloryczny u `General Nutritionista` przy jednoczesnym rozpoczęciu intensywnego bloku siłowego u `Climbing Coacha`):
1. Supervisor oznacza stan jako `GOAL_CONFLICT` i wstrzymuje automatyczne wdrożenie kolidujących zmian.
2. Specjaliści określają konsekwencje i przygotowują bezpieczne warianty alternatywne (np. Wariant A: zmniejszenie deficytu na czas bloku siłowego; Wariant B: redukcja objętości i intensywności treningu na czas redukcji masy).
3. Supervisor przedstawia użytkownikowi spójne podsumowanie obu wariantów i prosi o wybór priorytetu.


## 8. Safety & Escalation (Poziomy bezpieczeństwa i ograniczeń)

Każde ograniczenie zapisywane w systemie zawiera źródło oraz status weryfikacji (`confirmed` przez specjalistę, `user_reported` przez użytkownika, `agent_detected` przez model):

```json
{
  "restriction_id": "rest_001",
  "category": "training",
  "severity": "RESTRICTION",
  "affected_area": "right_ring_finger_a2",
  "restricted_actions": ["crimp_grip", "hangboard", "campus_board"],
  "status": "active",
  "source": "user_reported",
  "verification_status": "unverified_medical"
}
```

### Poziomy reakcji systemu:

- **WARNING (Ostrzeżenie):**
  - *Sygnały:* pogorszenie snu, przejściowe zmęczenie, zdarta skóra dłoni, krótkotrwałe wahanie masy.
  - *Działanie:* brak blokady systemowej; agent uwzględnia czynnik w bieżącym doborze ćwiczeń lub poradzie.
- **RESTRICTION (Lokalna blokada operacyjna):**
  - *Sygnały:* zgłoszony ból lokalny lub przeciążenie aparatu ruchu, aktywne ograniczenie rehabilitacyjne, sygnały zbyt niskiej dostępności energii (ryzyko RED-S) lub prośba o niebezpiecznie głęboki deficyt.
  - *Działanie:* Policy Validator blokuje możliwość zalecania ćwiczeń z listy `restricted_actions` (dla Trenera) lub dalszego obniżania kalorii (dla Dietetyka). Pozostałe, bezpieczne elementy systemu (np. trening core/mobilności, normalizacja diety) pozostają aktywne. System zaleca konsultację ze specjalistą (np. fizjoterapeutą).
- **CRITICAL ESCALATION (Krytyczna eskalacja i przerwanie przepływu):**
  - *Sygnały:* ostry uraz (np. trzask w palcu/barku, utrata funkcji, obrzęk), omdlenia, zawroty głowy, skrajne wyczerpanie, ostre zaburzenia odżywiania.
  - *Działanie:* natychmiastowe wstrzymanie generowania planów treningowych i redukcyjnych, anulowanie (`CANCELLED`) oczekujących propozycji zwiększających obciążenie oraz bezpośrednie zalecenie pilnej konsultacji lekarskiej.


## 9. Missing Data Handling (Obsługa niekompletnych danych)

- **Żywienie:** Brak wpisu o posiłku nie jest traktowany jako zerowe spożycie (głodówka). Dzień wyglądający na niepełny otrzymuje status `INCOMPLETE`, agent w razie potrzeby dopytuje użytkownika o brakujące posiłki, a Memory Manager wyklucza dni `INCOMPLETE` z wyliczania średnich tygodniowych i trendów zgodności z planem.
- **Trening i pomiary:** W przypadku braku kluczowych parametrów sesji lub protokołu testu agent prosi o uzupełnienie danych lub wykonuje analizę częściową, wyraźnie oznaczając poziom niepewności.


## 10. User Feedback & Recalibration (Odrzucanie propozycji i rekalibracja)

1. **Rzeczywistość ważniejsza niż plan:** Podczas rekalibracji mikrocyklu rzeczywiście wykonany trening i realny stan regeneracji mają zawsze wyższy priorytet niż pierwotne założenia planu.
2. **Szacunek dla decyzji użytkownika:** Odrzucenie propozycji (`REJECTED`) jest zapisywane w Memory Managerze (wraz z powodem, jeśli użytkownik go poda i wyrazi zgodę). Odrzucenie nie jest traktowane jako błąd użytkownika — agent nie może natarczywie ponawiać identycznej propozycji w kolejnej wiadomości, o ile nie pojawiły się nowe przesłanki bezpieczeństwa.


## 11. Inter-Agent Communication (Komunikacja między agentami)

1. Wszystkie komunikaty między komponentami (`TASK`, `RECOMMENDATION`, `PROPOSAL`, `MESSAGE`) muszą przechodzić walidację względem wspólnych schematów JSON.
2. Agent otrzymujący `RECOMMENDATION` od innego specjalisty nie traktuje jej jako automatycznego polecenia — ma obowiązek zweryfikować ją względem własnej bazy wiedzy oraz ograniczeń swojej domeny.
3. Pole `context_summary` służy wyłącznie jako zwięzły opis przyczyny rekomendacji i nie może być używane do przemycania surowych danych wrażliwych z pominięciem Memory Managera.


## 12. Confidence & Evidence (Pewność, estymacja i jakość dowodów)

1. **Hierarchia dowodów:** Rekomendacje merytoryczne powinny odwoływać się do rekordów wiedzy (`EvidenceRecord`) zgodnie z hierarchią: przeglądy systematyczne i metaanalizy → oficjalne wytyczne i konsensusy → badania RCT → badania obserwacyjne. Agenci nie mogą przedstawiać pojedynczego badania na małej próbie jako uniwersalnego prawa.
2. **Oznaczanie szacunków (`ESTIMATED`):** Dane z logowania posiłków językiem naturalnym (NLP) oraz przyszłej analizy zdjęć mają status `ESTIMATED` do czasu zatwierdzenia przez użytkownika.
3. **Zakaz pozornej precyzji:** Agenci nie dokonują sztywnych przeliczeń między nieporównywalnymi skalami wspinaczkowymi ani nie porównują ze sobą testów (`Assessments`) lub pomiarów tkanki tłuszczowej (BF%) wykonanych różnymi metodami i w różnych warunkach.


## 13. Policy Enforcement (Walidacja decyzji przed wykonaniem)

Przed zapisaniem jakiejkolwiek zmiany w bazie danych lub zwróceniem odpowiedzi użytkownikowi Policy Validator (w ramach Orchestratora) weryfikuje:
1. **Zgodność ze schematem:** Czy odpowiedź agenta jest poprawnym obiektem JSON zgodnym z kontraktem?
2. **Brak naruszenia restrykcji:** Czy proponowany trening lub plan żywieniowy nie narusza aktywnych flag `RESTRICTION` lub `CRITICAL ESCALATION` użytkownika?
3. **Autoryzację zapisu:** Czy próba modyfikacji planu posiada powiązany obiekt `PROPOSAL` ze statusem `ACCEPTED`?
4. **Uprawnienia do danych:** Czy zapytanie do Memory Managera mieści się w domyślnej macierzy uprawnień (Sekcja 2) lub posiada ważny token Task-scoped access (Sekcja 3)?
