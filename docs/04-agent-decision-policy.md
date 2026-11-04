# Agent Decision Policy — System Rules & Thresholds v0.1

## 1. Cel dokumentu

Dokument definiuje wspólne reguły decyzyjne, progi bezpieczeństwa, zasady autoryzacji zmian (`PROPOSAL`) oraz macierz uprawnień dostępu do danych dla wszystkich komponentów systemu: `Supervisora`, `Climbing Coacha` oraz `General Nutritionista`. 

Reguły te są egzekwowane dwutorowo:
1. **Programowo (przez `Orchestrator` i `Memory Manager`)** — walidacja schematów JSON, uprawnień dostępu i statusów.
2. **Instrukcyjnie (przez prompty systemowe agentów)** — klasyfikacja intencji, ocena ryzyka i merytoryczna analiza odchyleń.


# 2. Macierz dostępu do danych (Least Privilege Matrix)

`Memory Manager` udostępnia dane agentom wyłącznie zgodnie z poniższą macierzą uprawnień:

| Kategoria danych | Supervisor | Climbing Coach | General Nutritionist |
| :--- | :--- | :--- | :--- |
| Profil podstawowy (wiek, płeć, wzrost, masa) | Pełny odczyt | Pełny odczyt | Pełny odczyt |
| Główne cele i terminy | Pełny odczyt | Pełny odczyt | Pełny odczyt |
| Aktywne ograniczenia i flagi bezpieczeństwa | Pełny odczyt | Tylko aparat ruchu i sprzęt | Tylko dieta i interakcje lek–żywność |
| Szczegółowa historia treningów i wspinania | Tylko podsumowania | Pełny odczyt i zapis | Brak dostępu (tylko szacowany koszt/liczba sesji) |
| Standaryzowane testy (`Assessments`) | Brak dostępu | Pełny odczyt i zapis | Brak dostępu |
| Surowe dzienniki posiłków | Brak dostępu | Brak dostępu | Pełny odczyt i zapis |
| Trend masy i składu ciała (BF%) | Tylko podsumowania | Tylko aktualna masa | Pełny odczyt (wraz z metodą pomiaru) |
| Pełna historia medyczna / psychologiczna | Brak dostępu | Brak dostępu | Brak dostępu |


# 3. Reguły routingu i dekompozycji zapytań

`Supervisor` wybiera tryb obsługi według następującego drzewa decyzyjnego:

1. **Direct System Response (Bez wywoływania specjalistów):**
   - Zapytanie dotyczy wyłącznie statusu konta, aktywnych celów, listy oczekujących obiektów `PROPOSAL` lub możliwości systemu.
2. **Single-Domain Dispatch (Jeden specjalista):**
   - Zapytanie mieści się w 100% w domenie treningowej (`Climbing Coach`) lub żywieniowej (`General Nutritionist`) i nie narusza granic drugiego planu.
3. **Multi-Domain Decomposition (Równoległe wywołanie obu specjalistów):**
   - Zapytanie wprost łączy obie domeny (np. przygotowanie taktyczno-żywieniowe pod wyjazd w skały lub zawody).
   - Użytkownik zgłasza ogólnoustrojowy problem wieloczynnikowy (np. przewlekły spadek energii i siły na treningach).
4. **Ambiguity Resolution (Pytanie doprecyzowujące):**
   - Zapytanie jest zbyt krótkie lub wieloznaczne, by przypisać je do domeny, a wywołanie obu agentów wygenerowałoby zbędny koszt. `Supervisor` zadaje maksymalnie 1–2 konkretne pytania pomocnicze przed uruchomieniem specjalistów.


# 4. Definicja „Istotnej zmiany” i wymóg `PROPOSAL`

Żaden agent nie może wprowadzić trwałej modyfikacji w planie użytkownika bez wygenerowania obiektu `PROPOSAL` i uzyskania statusu `ACCEPTED`.

## 4.1. Działania niewymagające `PROPOSAL` (Tryb doradczy / Ad-hoc)
- Odpowiedzi na pytania edukacyjne i taktyczne (np. czas odpoczynku między wstawkami, propozycja posiłku przed wspinaniem).
- Zapisanie pojedynczego treningu, przejścia wspinaczkowego lub potwierdzonego posiłku.
- Drobna, jednorazowa korekta wewnątrz pojedynczej sesji na prośbę użytkownika (np. zamiana ćwiczenia rozgrzewkowego z powodu zajętego sprzętu na siłowni).

## 4.2. Działania bezwzględnie wymagające `PROPOSAL`
- **W domenie `Climbing Coach`:**
  - utworzenie nowego planu treningowego lub rozpoczęcie nowego mezocyklu,
  - zmiana liczby jednostek treningowych w tygodniu,
  - zmiana struktury mikrocyklu po wykryciu odstępstwa (rekalibracja planu),
  - zmiana docelowej intensywności lub objętości w kluczowych bojach/zwisach,
  - wprowadzenie nieplanowanego tygodnia regeneracyjnego (`deload` / `tapering`).
- **W domenie `General Nutritionist`:**
  - utworzenie lub zmiana docelowego bilansu kalorycznego,
  - zmiana docelowego rozkładu makroskładników,
  - zmiana głównego celu (np. przejście z redukcji na utrzymanie masy),
  - modyfikacja stałego planu posiłków.


# 5. Progi rekalibracji planu (Plan Recalibration Rules)

Agenci przed zaproponowaniem zmian oceniają rzeczywiste wykonanie planu względem założeń:

## 5.1. Rekalibracja treningowa (`Climbing Coach`)
Procedura rekalibracji jest uruchamiana, gdy:
- użytkownik wykonał nieplanowaną, obciążającą sesję (np. wyjazd w skały lub ciężki bouldering w zaplanowany dzień odpoczynku),
- użytkownik pominął kluczową jednostkę treningową w bieżącym mikrocyklu,
- raportowane RPE/zmęczenie lub pogorszenie stanu skóry dłoni uniemożliwia bezpieczne wykonanie kolejnej zaplanowanej jednostki.
**Zasada nadrzędna:** Rzeczywiste obciążenie zawsze ma priorytet nad teoretyczną rozpiską w kalendarzu.

## 5.2. Rekalibracja żywieniowa i walidacja luk (`General Nutritionist`)
1. **Weryfikacja kompletności (`Missing Data Gate`):** Przed oceną tygodniowego trendu kalorycznego system sprawdza kompletność dzienników. Dzień z anomalnie niską liczbą wpisów lub bez potwierdzenia użytkownika otrzymuje flagę `INCOMPLETE` i jest **wykluczany** ze średniej tygodniowej.
2. **Stabilność trendu masy:** Decyzje o korekcie kalorii mogą być podejmowane wyłącznie na podstawie trendu lub średniej kroczącej (minimum 7–14 dni), nigdy na podstawie pojedynczego ważenia.


# 6. Bramki bezpieczeństwa i progi eskalacji (Safety Gates)

System klasyfikuje sygnały ryzyka na trzech poziomach:

## Poziom 1: `WARNING` (Ostrzeżenie analityczne)
- **Wyzwalacze:**
  - pojedyncza noc słabego snu lub podwyższone subiektywne zmęczenie,
  - zdarty naskórek dłoni utrudniający chwyt,
  - krótkoterminowe wahanie masy ciała lub 1–2 dni niepełnego logowania posiłków.
- **Reakcja systemu:**
  - brak blokady systemowej; specjalista uwzględnia informację w bieżącej poradzie (np. sugestia dostosowania chwytów do stanu skóry lub przypomnienie o uzupełnieniu dziennika).

## Poziom 2: `RESTRICTION` (Lokalna blokada domeny/struktury)
- **Wyzwalacze treningowe:**
  - zgłoszenie lokalnego bólu lub przeciążenia (np. kłucie w troczku przy łuczku, ból łokcia przy podciąganiu),
  - aktywne ograniczenie rehabilitacyjne przypisane do profilu.
- **Wyzwalacze żywieniowe:**
  - prośba użytkownika o agresywny, niebezpieczny deficyt kaloryczny,
  - zbieżność sygnałów niskiej dostępności energii (spadek wydolności, pogorszenie regeneracji, nawracające przeciążenia — ryzyko RED-S).
- **Reakcja systemu:**
  - `Climbing Coach` ma zablokowaną możliwość planowania ćwiczeń obciążających bolesną strukturę (może planować trening antagonistyczny, core lub mobilność nieobciążającą urazu) i wysyła rekomendację konsultacji z fizjoterapeutą.
  - `General Nutritionist` ma zablokowaną możliwość proponowania dalszego cięcia kalorii; w razie potrzeby generuje `PROPOSAL` zwiększenia podaży energii lub przejścia na utrzymanie masy.

## Poziom 3: `CRITICAL ESCALATION` (Przerwanie przepływu)
- **Wyzwalacze:**
  - ostry uraz podczas aktywności (np. słyszalny trzask w palcu/barku, nagły obrzęk, utrata funkcji ruchowej lub czucia),
  - objawy ogólnoustrojowe (omdlenia, zawroty głowy, skrajne wyczerpanie, deklaracje wskazujące na ostre zaburzenia odżywiania).
- **Reakcja systemu:**
  - `Supervisor` natychmiast wstrzymuje generowanie planów treningowych i redukcyjnych, anuluje (`CANCELLED`) oczekujące propozycje zwiększające obciążenie i zwraca bezpośredni komunikat zalecający pilną konsultację lekarską.


# 7. Protokół rozwiązywania konfliktów międzyagentowych

Gdy rekomendacja jednego specjalisty koliduje z planem drugiego (np. `Climbing Coach` zgłasza rozpoczęcie ciężkiego bloku siły maksymalnej, podczas gdy w `General Nutritionist` aktywny jest głęboki deficyt kaloryczny):

1. `Supervisor` wstrzymuje automatyczne zatwierdzenie zmian i oznacza sytuację jako `GOAL_CONFLICT`.
2. `Supervisor` zleca obu agentom wygenerowanie krótkiej oceny ryzyka oraz wariantów kompromisowych:
   - **Wariant A (Priorytet: Wynik i siła):** zmniejszenie deficytu / przejście na zerowy bilans kaloryczny na czas trwania ciężkiego bloku treningowego.
   - **Wariant B (Priorytet: Redukcja masy):** obniżenie objętości i intensywności treningu wspinaczkowego do poziomu bezpiecznego dla regeneracji na deficycie.
3. `Supervisor` prezentuje oba warianty użytkownikowi w formie czytelnego wyboru i dopiero po decyzji użytkownika aktualizuje plany do statusu `APPLIED`.


# 8. Reguły rzetelności danych i estymacji (Epistemic Integrity)

1. **Brak pozornej precyzji wycen:** `Climbing Coach` zapisuje przejścia w oryginalnym systemie wyceny podanym przez użytkownika (np. skala francuska, Font, V-scale) i nie dokonuje sztywnych, automatycznych przeliczeń między skalami.
2. **Porównywalność pomiarów:** Wyniki testów (`Assessments`) oraz pomiary procentu tkanki tłuszczowej (BF%) mogą być zestawiane w trendzie tylko wtedy, gdy zostały wykonane według tego samego protokołu i tą samą metodą pomiarową.
3. **Oznaczanie szacunków (`ESTIMATED`):** Wszystkie wartości odżywcze wyliczone z opisu w języku naturalnym (NLP) lub ze zdjęcia posiadają status `ESTIMATED` do momentu jawnego potwierdzenia przez użytkownika.
4. **Weryfikacja rekomendacji:** Odbiorca komunikatu `RECOMMENDATION` zawsze weryfikuje go względem własnych reguł dziedzinowych i ograniczeń bezpieczeństwa użytkownika przed utworzeniem `PROPOSAL`.
