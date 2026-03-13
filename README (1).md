# Peace Situational Awareness Dashboard
### Powered by VIEWS fatalities003

---

## Projektirakenne

```
views_dashboard/
├── data/
│   ├── fatalities003_cm.csv      # country-month (lataamasi tiedosto)
│   ├── fatalities003_pgm.csv     # PRIO-GRID-month (sub-national)
│   └── dashboard_data.json       # generoitu export (luodaan automaattisesti)
├── src/
│   ├── data_processor.py         # datan lataus, suodatus, muunnokset
│   ├── views_api.py              # VIEWS REST API -client (live data)
│   └── app.py                    # Streamlit dashboard
├── requirements.txt
└── README.md
```

---

## Asennus

```bash
cd views_dashboard
pip install -r requirements.txt
```

---

## Käyttö

### 1. Streamlit dashboard (suositeltava aloitustapa)
```bash
cd src
streamlit run app.py
```
Avaa selaimessa: http://localhost:8501

### 2. Data-prosessointi suoraan
```bash
cd src
python data_processor.py
```
Tulostaa top-10 maat ja exportaa `data/dashboard_data.json`.

### 3. Live data VIEWS API:sta
```bash
cd src
python views_api.py
```
Hakee uusimman ennusteen suoraan viewsforecasting.org:sta.

---

## Tärkeimmät funktiot

### data_processor.py
| Funktio | Kuvaus |
|---|---|
| `load_cm()` | Lataa country-month CSV → DataFrame |
| `filter_countries(df, countries)` | Suodattaa valitut maat |
| `top_n_countries(df, n)` | Top-N eniten uhreja ennustavat maat |
| `pivot_timeseries(df)` | Pivotoi aikasarjaksi (maat = sarakkeet) |
| `to_dashboard_json(df)` | Exportaa JSON dashboard-käyttöön |
| `summary_table(df)` | Tiivistelmätaulu yhdelle kuukaudelle |

### views_api.py
| Metodi | Kuvaus |
|---|---|
| `get_cm_forecast(step=1)` | Yksittäinen step country-month |
| `get_pgm_forecast(step=1)` | Yksittäinen step sub-national |
| `get_cm_multistep(steps=[1..36])` | Kaikki 36 kuukautta kerralla |

---

## Datan kuvaus

| Sarake | Kuvaus |
|---|---|
| `country_id` | VIEWS sisäinen maa-ID |
| `month_id` | VIEWS sisäinen kuukausi-ID (554 = helmikuu 2026) |
| `country` | Maan nimi |
| `isoab` | ISO 3166-1 alpha-3 koodi |
| `year` / `month` | Vuosi ja kuukausi |
| `main_mean` | Ennustettu kuolonuhrimäärä (normaaliskaala) |
| `main_mean_ln` | Ennustettu kuolonuhrimäärä (ln-skaala) |
| `main_dich` | Todennäköisyys ≥25 taistelukuolemaa/kk |

---

## Jatkokehitysideoita

- [ ] Lisää PGM-tason karttavisualisointi (folium / pydeck)
- [ ] Yhdistä ACLED-data narratiiviseurantaan
- [ ] Automaattinen kuukausipäivitys VIEWS API:sta (cron / GitHub Actions)
- [ ] CMI-projektitietokanta RAG-pohjaiseen kyselyyn
- [ ] Ceasefire Clause Analyzer (RAG + peace agreement DB)

---

## Lähteet
- VIEWS Project: https://viewsforecasting.org
- API docs: https://viewsforecasting.org/data/
- Model docs: https://viewsforecasting.org/fatalities003/
- Uppsala University & PRIO (Peace Research Institute Oslo)
