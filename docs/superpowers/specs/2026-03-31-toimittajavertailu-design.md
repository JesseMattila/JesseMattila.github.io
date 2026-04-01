# Toimittajavertailu — Design Spec

**Päivämäärä:** 2026-03-31
**Status:** Draft
**Sijainti:** `tools/toimittajavertailu/`

## Yhteenveto

Python CLI -työkalu toimittajien vertailuun hankintatilanteessa. Laskee landed costin huomioiden maan, Incoterms-ehdon ja tilausvolyymin — näyttää mikä toimittaja on oikeasti edullisin kokonaisuutena. Esimerkkituotteena pihaharava.

Sama logiikka toteutetaan myöhemmin kevyenä web-demona GitHub Pages -portfolioon.

## Ongelma jonka työkalu ratkaisee

Halvin yksikköhinta ei ole halvin kokonaiskustannus. Kiinalainen 2.40€ harava voi olla kalliimpi kuin virolainen 7.20€ harava kun huomioidaan rahti, tulli, vakuutus, huolinta ja toimitusaika. Excel ei tee tätä näkyväksi yhdellä silmäyksellä.

## Kohderyhmä

1. **Portfolio-demo** — rekrytoija/HR näkee toimivan työkalun ja ymmärtää logiikan
2. **Käytännön työkalu** — hankinta- tai logistiikkaroolissa toimittajien vertailuun

## Tiedostorakenne

```
tools/toimittajavertailu/
├── supplier_comparison.py    # Pääskripti (yksi tiedosto)
├── README.md                 # Käyttöohje
└── examples/
    ├── pihaharavat.csv        # Pääesimerkki
    ├── pakkaustarvikkeet.csv  # Toinen toimiala
    └── logistiikka.csv        # Kolmas toimiala
```

## CSV-pohjan sarakkeet

| Sarake | Tyyppi | Esimerkki | Pakollinen |
|--------|--------|-----------|------------|
| toimittaja | teksti | "GardenTools OÜ" | kyllä |
| maa | teksti (10 maata) | "Viro" | kyllä |
| yksikkohinta_eur | numero | 7.20 | kyllä |
| incoterms | EXW/FOB/CIF/DDP | "FOB" | kyllä |
| toimitusaika_pv | numero | 14 | kyllä |
| maksuehto_pv | numero | 30 | kyllä |
| moq | numero | 300 | kyllä |
| laatu_arvio | 1-5 | 4 | kyllä |
| reklamaatio_pct | numero | 1.2 | ei |
| sertifikaatit | teksti | "ISO 9001" | ei |
| alennus_1000 | prosentti | 4 | ei |
| alennus_5000 | prosentti | 8 | ei |

## Tuetut maat (10 kpl, kovakoodattu)

| Maa | Rahti →HEL | Tulli-% | Lisäaika (pv) | EU | Riski (1-5) |
|-----|-----------|---------|---------------|-----|-------------|
| Suomi | 150€ | 0% | 1 | kyllä | 1 |
| Viro | 300€ | 0% | 2 | kyllä | 1 |
| Liettua | 450€ | 0% | 3 | kyllä | 1 |
| Puola | 700€ | 0% | 4 | kyllä | 1 |
| Saksa | 800€ | 0% | 4 | kyllä | 1 |
| Turkki | 1800€ | 4% | 12 | ei | 3 |
| Saudi-Arabia | 2800€ | 4% | 20 | ei | 3 |
| Intia | 3200€ | 5% | 30 | ei | 3 |
| Kiina | 3500€ | 6% | 35 | ei | 4 |
| USA | 2500€ | 3% | 18 | ei | 2 |

Jokaiselle maalle:
- Selkokielinen riskikuvaus (2-3 lausetta)
- Linkki ulkoministeriön matkustustiedotteeseen (um.fi)

## Incoterms (4 ehtoa)

| Ehto | Selkokieli | Ostaja maksaa |
|------|-----------|---------------|
| **EXW** | "Nouda tehtaalta" | Kaiken: lastaus, kuljetus, tulli, vakuutus |
| **FOB** | "Toimittaja vie satamaan/terminaaliin" | Merirahdista eteenpäin + tulli |
| **CIF** | "Rahti ja vakuutus maksettu" | Tullin + jatkokuljetuksen |
| **DDP** | "Toimitettu perille tullattuna" | Ei mitään — kaikki hinnassa |

### Landed cost -kaava

```
Kohde: Helsinki (kovakoodattu)

EXW:  yksikköhinta × kpl + rahti + (yksikköhinta × kpl × tulli-%) + vakuutus(1%) + huolinta(200€ ei-EU)
FOB:  yksikköhinta × kpl + rahti × 0.6 + (yksikköhinta × kpl × tulli-%) + vakuutus(1%) + huolinta(200€ ei-EU)
CIF:  yksikköhinta × kpl + (yksikköhinta × kpl × tulli-%) + huolinta(200€ ei-EU)
DDP:  yksikköhinta × kpl (kaikki sisältyy)
```

Käyttäjä voi vaihtaa toimittajan Incotermsiä ja nähdä miten landed cost muuttuu.

## Volyymilaskenta

Käyttäjä syöttää tilausmäärän → työkalu laskee jokaiselle toimittajalle:

1. **MOQ-tarkistus** — onko tilausmäärä ≥ MOQ? Jos ei → ⛔ ALLE MOQ
2. **Volyymialennus** — yli 1000 kpl ja yli 5000 kpl portaat (CSV:stä)
3. **Rahti per kappale** — kiinteä rahtikulu / kappalemäärä → laskee volyymin kasvaessa
4. **Landed cost per kappale** ja kokonaiskustannus

### Volyymi-optimointikäyrä

Lisävisualisointi: X-akseli = kappalemäärä, Y-akseli = landed cost per kappale per toimittaja. Näyttää missä kohtaa mikäkin toimittaja muuttuu kannattavaksi.

## Painotusprofiilit

| Profiili | Landed cost | Laatu | Toimitus | Riski | Maksuehto |
|----------|-------------|-------|----------|-------|-----------|
| **Tasapainoinen** | 25% | 25% | 20% | 20% | 10% |
| **Hintakriittinen** | 40% | 15% | 15% | 20% | 10% |
| **Laatukriittinen** | 15% | 35% | 20% | 20% | 10% |

**Huom:** "Hinta" = landed cost, ei yksikköhinta.

## Outputit

### 1. Ranking-taulukko (terminaaliin)

```
Tilaus: 1000 kpl pihaharavoja | Profiili: Tasapainoinen

  #  Toimittaja              Maa          Yksikkö  Landed/kpl  Yhteensä    Pisteet
  1  GardenTools OÜ          Viro          6.91€    7.21€       7 210€     84/100
  2  Baltijos Grėbliai UAB   Liettua       5.57€    6.02€       6 020€     82/100
  3  Gardena Polska          Puola         6.18€    6.88€       6 880€     79/100
  4  PuutarhaPro Oy          Suomi         8.63€    8.78€       8 780€     78/100
  5  RakeKing GmbH           Saksa         9.60€   10.40€      10 400€     72/100
  6  American Garden Tools   USA           7.13€    9.88€       9 880€     68/100
  7  Antalya Bahçe A.Ş.     Turkki        4.42€    6.80€       6 800€     65/100
  8  Riyadh Industrial       S-Arabia      3.90€    7.30€       7 300€     61/100
  9  Ningbo Garden Co        Kiina         2.33€    6.83€       6 830€     58/100
 10  Mumbai Garden Pvt       Intia         3.01€    6.72€       6 720€     55/100
```

### 2. Radar chart (matplotlib → PNG)

Jokainen toimittaja omana monikulmionaan. Akselit: Landed cost, Laatu, Toimitus, Riski, Maksuehto.

### 3. Maariski-yhteenveto

```
🇨🇳 Kiina — Korkea riski (4/5)
   Pitkät toimitusajat, geopoliittinen epävarmuus, tulliriskit. IP-suojan haasteet.
   → https://um.fi/matkustustiedotteet/-/maatiedot/kiina

🇸🇦 Saudi-Arabia — Kohtalainen riski (3/5)
   Vakaa talous, mutta kulttuurierot liiketoiminnassa. Logistiikka toimii.
   → https://um.fi/matkustustiedotteet/-/maatiedot/saudi-arabia
```

### 4. Incoterms-vertailu per toimittaja

```
Ningbo Garden Co (Kiina) — 1000 kpl:
  EXW:  2.33€/kpl → landed  6.83€/kpl  (+193%)
  FOB:  3.10€/kpl → landed  5.80€/kpl  (+87%)
  CIF:  4.50€/kpl → landed  5.00€/kpl  (+11%)
  DDP:  5.80€/kpl → landed  5.80€/kpl  (+0%)
```

### 5. Volyymi-optimointikäyrä (matplotlib → PNG)

X = kappalemäärä (100–10000), Y = landed cost per kappale. Eri väri per toimittaja. MOQ-raja merkitty pystyviivalla.

## Web-demo (myöhemmin)

- Sama logiikka HTML/JS:llä GitHub Pagesiin
- Valmiit esimerkkidatasetit (ei käyttäjän uploadia → ei turvariskiä)
- Hover-tooltip mailla: riskitiivistelmä + linkki um.fi
- Incoterms-vaihto lennosta
- Kappalemäärän säätö liukusäätimellä
- Chart.js radar chart + volyymikäyrä

## Esimerkkidata: pihaharavat.csv

```csv
toimittaja,maa,yksikkohinta_eur,incoterms,toimitusaika_pv,maksuehto_pv,moq,laatu_arvio,reklamaatio_pct,sertifikaatit,alennus_1000,alennus_5000
PuutarhaPro Oy,Suomi,8.90,DDP,3,14,100,5,0.5,"ISO 9001, Avainlippu",3,5
GardenTools OÜ,Viro,7.20,FOB,7,30,300,4,1.2,"ISO 9001",4,8
Baltijos Grėbliai UAB,Liettua,5.80,FOB,9,30,400,4,1.5,"ISO 9001",4,7
Gardena Polska,Puola,6.50,CIF,10,45,500,4,1.8,"ISO 9001, ISO 14001",5,10
RakeKing GmbH,Saksa,9.80,DDP,5,30,200,5,0.3,"ISO 9001, TÜV",2,4
Antalya Bahçe A.Ş.,Turkki,4.60,FOB,18,45,600,3,2.2,"TSE",4,8
Mumbai Garden Pvt,Intia,3.10,EXW,35,60,1500,3,3.0,"ISO 9001, BIS",3,6
Ningbo Garden Co,Kiina,2.40,EXW,45,60,2000,3,3.5,"ISO 9001",3,7
Riyadh Industrial,Saudi-Arabia,4.10,FOB,25,45,1000,3,2.8,"SASO",5,9
American Garden Tools Inc,USA,7.50,CIF,15,30,300,5,0.8,"ANSI, ISO 9001",2,5
```

## Tekniset riippuvuudet

- Python 3.10+
- pandas
- matplotlib
- Ei muita ulkoisia riippuvuuksia

## Rajaukset

- Valuutta: vain EUR
- Kohde: Helsinki (kovakoodattu)
- Maat: 10 kovakoodattua
- Incoterms: 4 ehtoa (EXW, FOB, CIF, DDP)
- Ei tietokantaa — kaikki CSV-pohjaisesti
- Ei API-kutsuja — maariskit kovakoodattuna
