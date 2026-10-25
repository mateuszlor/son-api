# Plan zmiany: REST API do zdalnego wykorzystania danych SON

## 1. Cel i zakres

Dodanie interfejsu HTTP (REST API) nad istniejącą biblioteką `lib/son_client.py`,
tak aby zewnętrzne systemy mogły **zdalnie pobierać dane z panelu SON w ustrukturyzowanej formie (JSON)**
i wykorzystywać je w automatyzacjach (skrypty, integracje), bez ręcznego uruchamiania
skryptów CLI i bez parsowania HTML/CSV.

Zakres **nie** obejmuje wykonywania skryptów (`fetch_all_data.py`, `fetch_latest_invoice.py`) jako jobów.
API udostępnia dane i operacje biblioteki `SONInternalClient` w formie endpointów HTTP.
Istniejące skrypty pozostają bez zmian (mogą korzystać z API lub działać jak dotąd).

## 2. Obecny stan

- `lib/son_client.py` (`SONInternalClient`) udostępnia metody: `get_tenants`, `get_estates`,
  `get_tenant_operations`, `get_tenant_liabilities`, `get_insurances`, `get_finances`,
  `get_estate_cost_documents`, `get_cost_document_download_url`, `download_file`,
  `parse_*`, `normalize_url`, `fetch_invoice_pdfs`.
- Skrypty CLI (`fetch_all_data.py`, `fetch_latest_invoice.py`) korzystają z klienta i zapisują CSV/PDF.
- Brak warstwy HTTP; dane dostępne tylko przez uruchamianie skryptów.

## 3. Wymagania

### Funkcjonalne

1. Endpointy zwracające sparsowane dane (JSON) z panelu SON:
   - najemcy, nieruchomości, operacje najemcy, zobowiązania, ubezpieczenia,
   - finanse właściciela, dokumenty kosztowe nieruchomości.
2. Pobieranie plików PDF (faktury, dokumenty kosztowe) przez API.
3. Sprawdzenie stanu serwisu (`/health`).
4. Automatyczne logowanie i odświeżanie sesji SON (wewnątrz klienta).
5. Opcjonalne filtrowanie/paginacja zgodna z DataTables (parametry query).

### Niefunkcjonalne

- Lokalne, otwarte API (brak uwierzytelniania w v1).
- Jeden aktywny request SON jednocześnie (blokada sesji).
- Brak wycieku sekretów (login/hasło) w odpowiedziach i logach.
- HTTPS przez reverse proxy przy wystawieniu zewnętrzny.
- Prostota: jeden proces Python, zależności w `requirements.txt`.

## 4. Architektura

- Framework: **FastAPI** + **Uvicorn** (automatyczna dokumentacja OpenAPI).
- Klient SON: współdzielona instancja (singleton) z blokadą (`threading.Lock`),
  aby nie psuć sesji/CSRF przy równoległych requestach.
- Parsowanie: użycie istniejących metod `parse_*` z `SONInternalClient`.
- Pliki: serwowanie tylko spod `OUT_DIR` z walidacją ścieżki (ochrona przed path traversal).
- Brak bazy danych, brak kolejki jobów, brak wykonywania skryptów.

Komponenty:

```
api_server.py (root, executable)
  |- lib/api_models.py        (modele pydantic dla odpowiedzi)
  |- lib/api_son.py           (wrapper: singleton klienta + lock + konwersja do JSON)
  |- lib/path_safety.py       (bezpieczne ścieżki pod OUT_DIR)
```

## 5. Zmiany w strukturze repozytorium

Dodane pliki:
- `api_server.py` – punkt wejścia FastAPI.
- `lib/api_models.py`
- `lib/api_son.py`
- `lib/path_safety.py`
- `docs/api_usage.md` (po implementacji: przykłady curl/PowerShell)

Zmodyfikowane:
- `requirements.txt` – dodanie `fastapi`, `uvicorn[standard]`.
- `.gitignore` – ignorowanie plików tymczasowych.

Bez zmian:
- `fetch_all_data.py`, `fetch_latest_invoice.py`, `lib/son_client.py`.

## 6. Konfiguracja

Istniejące zmienne `.env`:
- `SON_LOGIN`, `SON_PASSWORD`, `SON_PANEL_URL`, `SON_OUT_DIR`.

Nowe (opcjonalne):
- `API_HOST=127.0.0.1`
- `API_PORT=8000`

Brak kluczy API, brak magazynu stanu.

## 7. Endpointy API (v1)

Brak uwierzytelniania (lokalne, otwarte API).

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/health` | Stan serwisu. |
| GET | `/v1/tenants` | Lista najemców (paginacja DataTables). |
| GET | `/v1/tenants/{id}` | Szczegóły najemcy (z `/tenants/view/{id}`? lub z listy). |
| GET | `/v1/tenants/{id}/operations` | Operacje najemcy (sparsowane). |
| GET | `/v1/tenants/{id}/liabilities` | Zobowiązania najemcy (sparsowane). |
| GET | `/v1/tenants/{id}/insurances` | Ubezpieczenia najemcy (sparsowane). |
| GET | `/v1/estates` | Lista nieruchomości. |
| GET | `/v1/estates/{id}/cost-documents` | Dokumenty kosztowe nieruchomości (sparsowane). |
| GET | `/v1/finances` | Finanse właściciela (sparsowane). |
| GET | `/v1/artifacts/{path}` | Pobranie pliku spod `OUT_DIR` (PDF/CSV). |

Kody odpowiedzi: 200, 400, 404, 500. Błędy SON (logowanie, CSRF, 429) mapowane na 502/503 z komunikatem (bez sekretów).

## 8. Modele odpowiedzi (JSON)

Na bazie istniejących struktur z `son_integration_models.md`:
- `Tenant`, `Operation`, `Liability`, `Insurance`, `Finance`, `CostDocument`.
- Dodatkowe pola: `pdf_url` (jeśli dostępny), `is_payout` dla dokumentów kosztowych.

Daty zwracane jako ISO (`YYYY-MM-DD`) lub `null`; kwoty jako liczby (float) lub `null`.

## 9. Bezpieczeństwo

1. Lokalne, otwarte API (brak auth) dla `127.0.0.1`/`localhost`.
2. Dostęp zewnętrzny: reverse proxy (HTTPS) i/lub VPN; brak kluczy API w v1.
3. Walidacja ścieżek artefaktów (`realpath` + prefiks `OUT_DIR`).
4. Brak ekspozycji `.env` i katalogu repo.
5. CORS wyłączony domyślnie.
6. Brak logowania loginu/hasła; redakcja w logach.

## 10. Współbieżność i sesja SON

- Współdzielona instancja `SONInternalClient` z blokadą `threading.Lock`.
- Każdy request wykonuje operację pod lockiem (jeden aktywny request SON).
- Przy wygaśnięciu sesji klient re-loguje się automatycznie (już w `_login`).
- Retry przy 429/5xx (już w `_get`/`_post`).

## 11. Harmonogram faz

### Faza 0 – przygotowanie (0.5 dnia)
- Dodanie zależności do `requirements.txt`.
- Utworzenie szkieletu plików.

### Faza 1 – wrapper SON (1 dzień)
- `lib/api_son.py`: singleton klienta, lock, konwersja HTML/JSON do modeli.
- `lib/path_safety.py`.
- Testy jednostkowe (mock klienta).

### Faza 2 – API (2 dni)
- `api_server.py` z endpointami z sekcji 7.
- Modele pydantic w `lib/api_models.py`.
- Obsługa błędów i mapowanie na kody HTTP.
- Walidacja parametrów (paginacja, id).

### Faza 3 – dokumentacja i wdrożenie (1 dzień)
- `docs/api_usage.md` z przykładami (curl, PowerShell).
- Instrukcja uruchomienia (dev + reverse proxy).
- Aktualizacja `.gitignore`.

Szacowany czas: ~4.5 dnia roboczego.

## 12. Testy i kryteria akceptacji

Testy jednostkowe:
- path safety (odrzucanie `..`, symlinków).
- konwersja modeli (daty, kwoty, `null`).

Testy integracyjne:
- `/health` zwraca 200.
- `/v1/tenants` zwraca listę JSON.
- `/v1/tenants/{id}/operations` zwraca sparsowane operacje.
- `/v1/finances` zwraca sparsowane finanse.
- Pobranie PDF przez `/v1/artifacts/...` zwraca `application/pdf`.
- Błędne id → 404.

Kryteria akceptacji:
1. Zewnętrzny klient może pobrać listę najemców i operacje w JSON przez HTTP.
2. Istniejące skrypty działają bez zmian.
3. Dokumentacja OpenAPI dostępna pod `/docs`.

## 13. Ryzyka i mitigacje

| Ryzyko | Mitigacja |
|---|---|
| Równoległe requesty psują sesję SON | Lock (jeden aktywny request). |
| Długie odpowiedzi (dużo danych) | Paginacja/limity; streaming w przyszłości. |
| Path traversal przy pobieraniu plików | `path_safety`. |
| Wyciek sekretów | Brak sekretów w odpowiedziach/logach. |
| Zmiana endpointów SON | API mapuje na istniejące metody; aktualizacja w jednym miejscu. |

## 14. Kompatybilność i migracja

- Brak breaking changes: skrypty i `lib/son_client.py` bez zmian.
- Nowe zależności w `requirements.txt`.
- API opcjonalne: brak konieczności uruchamiania serwera dla dotychczasowych przepływów CLI.

## 15. Decyzje

1. Framework: **FastAPI** (rekomendowany; porownanie w poprzedniej wersji planu).
2. Uwierzytelnianie: **brak w v1** (lokalne, otwarte API).
3. Zakres: **tylko odczyt danych** (GET). Zapis/akcje (np. zatwierdzanie dokumentów) poza v1.
4. Współbieżność: **lock** (jeden aktywny request SON).

---

## 16. Docker i hosting

API będzie hostowane w Dockerze.

### Pliki
- `Dockerfile` – obraz Python (slim), instalacja zależności, kopiowanie kodu, uruchomienie Uvicorn.
- `docker-compose.yml` – serwis `son-api`, port mapowany na hosta, wolumen dla `OUT_DIR`, zmienne z `.env`.
- `.dockerignore` – wykluczenie `.env`, `invoices/`, `__pycache__`, `.git`.

### docker-compose.yml (szkic)
```yaml
services:
  son-api:
    build: .
    ports:
      - "${API_PORT:-8000}:8000"
    env_file:
      - .env
    environment:
      - API_HOST=0.0.0.0
    volumes:
      - son_data:/app/invoices
    restart: unless-stopped

volumes:
  son_data:
```

### Uwagi
- W kontenerze `API_HOST=0.0.0.0` (nasłuch wewnątrz kontenera).
- `OUT_DIR` wskazuje na wolumen (np. `/app/invoices`), aby pliki przetrwały restart.
- `.env` nie jest kopiowany do obrazu (tylko `env_file` w compose).
- HTTPS zapewniane przez reverse proxy poza kontenerem (lub Traefik/Caddy w compose).

### Zmiany w strukturze
Dodane pliki: `Dockerfile`, `docker-compose.yml`, `.dockerignore`.

---

*Plan przygotowany dla repozytorium `goldensquare` (gałąź `feature/son-panel-automation`).*