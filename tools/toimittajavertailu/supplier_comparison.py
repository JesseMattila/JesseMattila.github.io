#!/usr/bin/env python3
"""
Toimittajavertailu — Landed Cost Calculator

Vertailee toimittajia kokonaiskustannuksen (landed cost) perusteella.
Huomioi maan, Incoterms-ehdon, volyymin, laadun ja riskin.

Käyttö:
    python supplier_comparison.py examples/pihaharavat.csv --qty 1000
    python supplier_comparison.py examples/pihaharavat.csv --qty 1000 --profile hintakriittinen
    python supplier_comparison.py examples/pihaharavat.csv --qty 1000 --incoterms CIF
    python supplier_comparison.py examples/pihaharavat.csv --qty 1000 --override "Ningbo Garden Co:DDP"
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# ──────────────────────────────────────────────
# KERROS 1: Kovakoodattu data
# ──────────────────────────────────────────────

# Coface-luokitukset: A1 (paras) → A2 → A3 → A4 → B → C → D → E (huonoin)
# Numeerinen skaala pisteytystä varten: A1=1, A2=2, A3=3, A4=4, B=5, C=6, D=7, E=8
COFACE_NUMERO = {"A1": 1, "A2": 2, "A3": 3, "A4": 4, "B": 5, "C": 6, "D": 7, "E": 8}

MAAT = {
    "Suomi":        {"rahti": 150,  "tulli_pct": 0,    "lisaaika_pv": 1,  "eu": True,  "coface_maa": "A3", "coface_bisnes": "A1", "coface_url": "https://www.coface.com/news-economy-and-insights/business-risk-dashboard/country-risk-files/finland"},
    "Viro":         {"rahti": 300,  "tulli_pct": 0,    "lisaaika_pv": 2,  "eu": True,  "coface_maa": "A3", "coface_bisnes": "A1", "coface_url": "https://www.coface.com/news-economy-and-insights/business-risk-dashboard/country-risk-files/estonia"},
    "Liettua":      {"rahti": 450,  "tulli_pct": 0,    "lisaaika_pv": 3,  "eu": True,  "coface_maa": "A4", "coface_bisnes": "A1", "coface_url": "https://www.coface.com/news-economy-and-insights/business-risk-dashboard/country-risk-files/lithuania"},
    "Puola":        {"rahti": 700,  "tulli_pct": 0,    "lisaaika_pv": 4,  "eu": True,  "coface_maa": "A3", "coface_bisnes": "A2", "coface_url": "https://www.coface.com/news-economy-and-insights/business-risk-dashboard/country-risk-files/poland"},
    "Saksa":        {"rahti": 800,  "tulli_pct": 0,    "lisaaika_pv": 4,  "eu": True,  "coface_maa": "A3", "coface_bisnes": "A1", "coface_url": "https://www.coface.com/news-economy-and-insights/business-risk-dashboard/country-risk-files/germany"},
    "Turkki":       {"rahti": 1800, "tulli_pct": 0.04, "lisaaika_pv": 12, "eu": False, "coface_maa": "C",  "coface_bisnes": "A4", "coface_url": "https://www.coface.com/news-economy-and-insights/business-risk-dashboard/country-risk-files/turkey"},
    "Saudi-Arabia": {"rahti": 2800, "tulli_pct": 0.04, "lisaaika_pv": 20, "eu": False, "coface_maa": "A3", "coface_bisnes": "B",  "coface_url": "https://www.coface.com/news-economy-and-insights/business-risk-dashboard/country-risk-files/saudi-arabia"},
    "Intia":        {"rahti": 3200, "tulli_pct": 0.05, "lisaaika_pv": 30, "eu": False, "coface_maa": "B",  "coface_bisnes": "A4", "coface_url": "https://www.coface.com/news-economy-and-insights/business-risk-dashboard/country-risk-files/india"},
    "Kiina":        {"rahti": 3500, "tulli_pct": 0.06, "lisaaika_pv": 35, "eu": False, "coface_maa": "B",  "coface_bisnes": "B",  "coface_url": "https://www.coface.com/news-economy-and-insights/business-risk-dashboard/country-risk-files/china"},
    "USA":          {"rahti": 2500, "tulli_pct": 0.03, "lisaaika_pv": 18, "eu": False, "coface_maa": "A2", "coface_bisnes": "A1", "coface_url": "https://www.coface.com/news-economy-and-insights/business-risk-dashboard/country-risk-files/united-states-of-america"},
}

MAARISKIT = {
    "Suomi":        "Kotimainen toimittaja. Ei logistisia riskejä, nopea toimitus.",
    "Viro":         "EU-naapurimaa. Lyhyt toimitusmatka, ei tullia. Luotettava.",
    "Liettua":      "EU-maa, Baltia. Edullinen tuotanto, hyvä infra. Ei tullia.",
    "Puola":        "EU:n suurin itäinen talous. Vahva teollisuus, ei tullia.",
    "Saksa":        "Korkea laatu ja luotettavuus. Premium-hintataso. EU-maa.",
    "Turkki":       "EU:n ulkopuolella. Tulliriskit, valuuttavaihtelut (liira). Kohtuullinen logistiikka.",
    "Saudi-Arabia": "Vakaa talous, mutta kulttuurierot liiketoiminnassa. Logistiikka toimii.",
    "Intia":        "Halpa tuotanto mutta pitkät toimitusajat. Laadunvaihtelu. Byrokratiaa.",
    "Kiina":        "Pitkät toimitusajat, geopoliittinen epävarmuus, tulliriskit. IP-suojan haasteet.",
    "USA":          "Korkea laatu, mutta kallis logistiikka Eurooppaan. Dollarivaihtelut.",
}

INCOTERMS_SELITE = {
    "EXW": "Nouda tehtaalta — ostaja maksaa kaiken: lastaus, kuljetus, tulli, vakuutus",
    "FOB": "Toimittaja vie satamaan — ostaja maksaa merirahdista eteenpäin + tulli",
    "CIF": "Rahti ja vakuutus maksettu — ostaja maksaa tullin + jatkokuljetuksen",
    "DDP": "Toimitettu perille tullattuna — kaikki hinnassa",
}

VAKUUTUS_PCT = 0.01
HUOLINTA_EI_EU = 200

PROFIILIT = {
    "tasapainoinen":   {"landed_cost": 0.25, "laatu": 0.25, "toimitus": 0.20, "riski": 0.20, "maksuehto": 0.10},
    "hintakriittinen": {"landed_cost": 0.40, "laatu": 0.15, "toimitus": 0.15, "riski": 0.20, "maksuehto": 0.10},
    "laatukriittinen": {"landed_cost": 0.15, "laatu": 0.35, "toimitus": 0.20, "riski": 0.20, "maksuehto": 0.10},
}


# ──────────────────────────────────────────────
# KERROS 2: Landed cost -laskenta
# ──────────────────────────────────────────────

def lue_csv(polku: str) -> list[dict]:
    """Lukee toimittaja-CSV:n ja palauttaa listan dictejä."""
    rivit = []
    with open(polku, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for rivi in reader:
            rivit.append({
                "toimittaja":      rivi["toimittaja"].strip(),
                "maa":             rivi["maa"].strip(),
                "yksikkohinta":    float(rivi["yksikkohinta_eur"]),
                "incoterms":       rivi["incoterms"].strip().upper(),
                "toimitusaika_pv": int(rivi["toimitusaika_pv"]),
                "maksuehto_pv":    int(rivi["maksuehto_pv"]),
                "moq":             int(rivi["moq"]),
                "laatu":           int(rivi["laatu_arvio"]),
                "reklamaatio_pct": float(rivi.get("reklamaatio_pct", 0) or 0),
                "sertifikaatit":   rivi.get("sertifikaatit", ""),
                "alennus_1000":    float(rivi.get("alennus_1000", 0) or 0),
                "alennus_5000":    float(rivi.get("alennus_5000", 0) or 0),
            })
    return rivit


def volyymialennus(yksikkohinta: float, qty: int, alennus_1000: float, alennus_5000: float) -> float:
    """Palauttaa alennetun yksikköhinnan."""
    if qty >= 5000 and alennus_5000 > 0:
        return yksikkohinta * (1 - alennus_5000 / 100)
    elif qty >= 1000 and alennus_1000 > 0:
        return yksikkohinta * (1 - alennus_1000 / 100)
    return yksikkohinta


def laske_landed_cost(toimittaja: dict, qty: int, incoterms_override: str | None = None) -> dict:
    """
    Laskee landed cost per kappale ja kokonaiskustannuksen.

    Palauttaa dictin jossa alkuperäiset tiedot + lasketut kentät.
    """
    maa = toimittaja["maa"]
    if maa not in MAAT:
        raise ValueError(f"Tuntematon maa: {maa}. Tuetut: {', '.join(MAAT.keys())}")

    maa_data = MAAT[maa]
    incoterms = incoterms_override or toimittaja["incoterms"]

    if incoterms not in INCOTERMS_SELITE:
        raise ValueError(f"Tuntematon Incoterms: {incoterms}. Tuetut: {', '.join(INCOTERMS_SELITE.keys())}")

    # Volyymialennettu yksikköhinta
    hinta = volyymialennus(
        toimittaja["yksikkohinta"], qty,
        toimittaja["alennus_1000"], toimittaja["alennus_5000"]
    )

    tavarahinta = hinta * qty
    rahti = maa_data["rahti"]
    tulli = tavarahinta * maa_data["tulli_pct"]
    vakuutus = tavarahinta * VAKUUTUS_PCT
    huolinta = HUOLINTA_EI_EU if not maa_data["eu"] else 0

    # Incoterms-kaavat
    if incoterms == "EXW":
        landed_total = tavarahinta + rahti + tulli + vakuutus + huolinta
    elif incoterms == "FOB":
        landed_total = tavarahinta + rahti * 0.6 + tulli + vakuutus + huolinta
    elif incoterms == "CIF":
        landed_total = tavarahinta + tulli + huolinta
    elif incoterms == "DDP":
        landed_total = tavarahinta
    else:
        raise ValueError(f"Tuntematon Incoterms: {incoterms}")

    landed_per_kpl = landed_total / qty
    alle_moq = qty < toimittaja["moq"]

    kokonaisaika = toimittaja["toimitusaika_pv"] + maa_data["lisaaika_pv"]

    return {
        **toimittaja,
        "incoterms_used":   incoterms,
        "alennettu_hinta":  hinta,
        "tavarahinta":      tavarahinta,
        "rahti":            rahti,
        "tulli":            tulli,
        "vakuutus":         vakuutus,
        "huolinta":         huolinta,
        "landed_total":     landed_total,
        "landed_per_kpl":   landed_per_kpl,
        "alle_moq":         alle_moq,
        "kokonaisaika_pv":  kokonaisaika,
        "coface_maa":       maa_data["coface_maa"],
        "coface_bisnes":    maa_data["coface_bisnes"],
        "coface_url":       maa_data["coface_url"],
        "maa_riski":        COFACE_NUMERO[maa_data["coface_maa"]],
    }


# ──────────────────────────────────────────────
# KERROS 3: Pisteytys
# ──────────────────────────────────────────────

def pisteyta(tulokset: list[dict], profiili_nimi: str) -> list[dict]:
    """
    Normalisoi ulottuvuudet 0–1 ja laskee painotetun kokonaispistemäärän.
    Palauttaa tulokset järjestettynä parhaasta huonoimpaan.
    """
    profiili = PROFIILIT[profiili_nimi]

    # Kerää arvot normalisointia varten
    landed_costs = [t["landed_per_kpl"] for t in tulokset]
    laadut = [t["laatu"] for t in tulokset]
    ajat = [t["kokonaisaika_pv"] for t in tulokset]
    riskit = [t["maa_riski"] for t in tulokset]
    maksuehdot = [t["maksuehto_pv"] for t in tulokset]

    def normalisoi_kaanteinen(arvo, minimi, maksimi):
        """Pienempi arvo = parempi → saa korkeamman pisteen."""
        if maksimi == minimi:
            return 1.0
        return 1.0 - (arvo - minimi) / (maksimi - minimi)

    def normalisoi(arvo, minimi, maksimi):
        """Suurempi arvo = parempi → saa korkeamman pisteen."""
        if maksimi == minimi:
            return 1.0
        return (arvo - minimi) / (maksimi - minimi)

    for t in tulokset:
        pisteet = {}

        # Landed cost: halvempi = parempi
        pisteet["landed_cost"] = normalisoi_kaanteinen(
            t["landed_per_kpl"], min(landed_costs), max(landed_costs)
        )
        # Laatu: korkeampi = parempi
        pisteet["laatu"] = normalisoi(
            t["laatu"], min(laadut), max(laadut)
        )
        # Toimitusaika: lyhyempi = parempi
        pisteet["toimitus"] = normalisoi_kaanteinen(
            t["kokonaisaika_pv"], min(ajat), max(ajat)
        )
        # Riski: pienempi = parempi
        pisteet["riski"] = normalisoi_kaanteinen(
            t["maa_riski"], min(riskit), max(riskit)
        )
        # Maksuehto: pidempi = parempi (ostaja saa enemmän maksuaikaa = ilmaista rahoitusta)
        pisteet["maksuehto"] = normalisoi(
            t["maksuehto_pv"], min(maksuehdot), max(maksuehdot)
        )

        # Painotettu kokonaispistemäärä
        kokonais = sum(pisteet[k] * profiili[k] for k in profiili)
        t["pisteet_osa"] = pisteet
        t["pisteet"] = round(kokonais * 100)

    tulokset.sort(key=lambda t: t["pisteet"], reverse=True)
    return tulokset


# ──────────────────────────────────────────────
# KERROS 4: Tulostus
# ──────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"


def tulosta_ranking(tulokset: list[dict], qty: int, profiili_nimi: str):
    """Tulostaa ranking-taulukon terminaaliin."""
    print()
    print(f"{BOLD}{'═' * 90}{RESET}")
    print(f"{BOLD}  TOIMITTAJAVERTAILU — {qty} kpl | Profiili: {profiili_nimi.title()}{RESET}")
    print(f"{BOLD}{'═' * 90}{RESET}")
    print()

    # Otsikkorivi
    print(f"  {'#':>2}  {'Toimittaja':<26} {'Maa':<14} {'Ehto':<5} {'Yksikkö':>8} {'Landed/kpl':>11} {'Yhteensä':>11} {'Pisteet':>8}")
    print(f"  {'─' * 2}  {'─' * 26} {'─' * 14} {'─' * 5} {'─' * 8} {'─' * 11} {'─' * 11} {'─' * 8}")

    for i, t in enumerate(tulokset, 1):
        moq_merkki = f" {RED}⛔ MOQ{RESET}" if t["alle_moq"] else ""

        if i == 1:
            vari = GREEN
        elif i <= 3:
            vari = CYAN
        elif t["alle_moq"]:
            vari = RED
        else:
            vari = ""

        rivi = (
            f"  {vari}{i:>2}  {t['toimittaja']:<26} {t['maa']:<14} {t['incoterms_used']:<5}"
            f" {t['alennettu_hinta']:>7.2f}€ {t['landed_per_kpl']:>10.2f}€"
            f" {t['landed_total']:>10,.0f}€ {t['pisteet']:>6}/100{RESET}{moq_merkki}"
        )
        print(rivi)

    print()


def tulosta_incoterms_vertailu(tulokset: list[dict], qty: int):
    """Tulostaa jokaisen toimittajan landed costin kaikilla neljällä Incoterms-ehdolla."""
    print(f"{BOLD}{'═' * 90}{RESET}")
    print(f"{BOLD}  INCOTERMS-VERTAILU — {qty} kpl{RESET}")
    print(f"{BOLD}{'═' * 90}{RESET}")
    print()

    for t in tulokset:
        print(f"  {BOLD}{t['toimittaja']}{RESET} ({t['maa']})")
        for ehto in ["EXW", "FOB", "CIF", "DDP"]:
            tulos = laske_landed_cost(t, qty, incoterms_override=ehto)
            merkki = " ◀ CSV" if ehto == t["incoterms"] else ""
            lisaprosentti = ((tulos["landed_per_kpl"] / tulos["alennettu_hinta"]) - 1) * 100
            print(
                f"    {ehto:<4}  {tulos['alennettu_hinta']:>6.2f}€/kpl → landed {tulos['landed_per_kpl']:>6.2f}€/kpl"
                f"  ({DIM}+{lisaprosentti:>5.1f}%{RESET}){merkki}"
            )
        print()


def coface_vari(luokitus: str) -> str:
    """Palauttaa terminaalivärin Coface-luokituksen mukaan."""
    if luokitus in ("A1", "A2"):
        return GREEN
    elif luokitus in ("A3", "A4"):
        return CYAN
    elif luokitus == "B":
        return YELLOW
    else:  # C, D, E
        return RED


def tulosta_maariskit(tulokset: list[dict]):
    """Tulostaa maariski-yhteenvedon Coface-luokituksilla."""
    print(f"{BOLD}{'═' * 90}{RESET}")
    print(f"{BOLD}  MAARISKI-YHTEENVETO (Coface){RESET}")
    print(f"{BOLD}{'═' * 90}{RESET}")
    print()

    nahdyt = set()
    for t in tulokset:
        maa = t["maa"]
        if maa in nahdyt:
            continue
        nahdyt.add(maa)

        maa_data = MAAT[maa]
        cm = maa_data["coface_maa"]
        cb = maa_data["coface_bisnes"]

        print(f"  {coface_vari(cm)}{maa} — Country Risk: {cm} | Business Climate: {cb}{RESET}")
        print(f"    {DIM}{MAARISKIT[maa]}{RESET}")
        print(f"    {DIM}→ {maa_data['coface_url']}{RESET}")
        print()


def luo_kuvaajat(tulokset: list[dict], qty: int, profiili_nimi: str, output_dir: Path):
    """Luo radar chart ja volyymikäyrä matplotlib:llä."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print(f"  {YELLOW}⚠ matplotlib ei asennettu — kuvaajia ei luoda.{RESET}")
        print(f"    Asenna: pip install matplotlib")
        print()
        return

    # ── Radar chart (small multiples) ──
    kategoriat = ["Hinta", "Laatu", "Toimitus", "Riski", "Maksuehto"]
    avaimet = ["landed_cost", "laatu", "toimitus", "riski", "maksuehto"]
    N = len(kategoriat)
    kulmat = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    kulmat += kulmat[:1]

    n_toimittajat = len(tulokset)
    cols = 5
    rows = (n_toimittajat + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(22, rows * 5),
                             subplot_kw=dict(polar=True))
    axes_flat = axes.flatten() if n_toimittajat > 1 else [axes]

    värit = plt.cm.tab10(np.linspace(0, 1, n_toimittajat))

    # Värikoodaus sijoituksen mukaan
    def sijoitus_vari(i):
        if i == 0:
            return "#22c55e"  # vihreä — #1
        elif i <= 2:
            return "#3b82f6"  # sininen — top 3
        elif i >= n_toimittajat - 2:
            return "#ef4444"  # punainen — bottom 2
        return "#6b7280"      # harmaa — keskikasti

    for i, t in enumerate(tulokset):
        ax = axes_flat[i]
        arvot = [t["pisteet_osa"][k] for k in avaimet]
        arvot += arvot[:1]

        # Harmaa tausta-monikulmio referenssiksi (mediaani = 0.5)
        ref = [0.5] * N + [0.5]
        ax.fill(kulmat, ref, alpha=0.06, color="#9ca3af")
        ax.plot(kulmat, ref, linewidth=0.5, color="#9ca3af", linestyle="--")

        # Toimittajan monikulmio
        vari = sijoitus_vari(i)
        ax.plot(kulmat, arvot, linewidth=2.5, color=vari)
        ax.fill(kulmat, arvot, alpha=0.20, color=vari)

        # Pisteet kulmiin
        for j, (kulma, arvo) in enumerate(zip(kulmat[:-1], arvot[:-1])):
            ax.text(kulma, arvo + 0.08, f"{arvo:.2f}", ha="center", va="center",
                    fontsize=7, color="#374151", fontweight="bold")

        ax.set_xticks(kulmat[:-1])
        ax.set_xticklabels(kategoriat, size=8)
        ax.set_ylim(0, 1)
        ax.set_yticks([0.25, 0.5, 0.75])
        ax.set_yticklabels(["", "", ""], size=6)
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)

        # Otsikko: sijoitus + nimi + pisteet
        moq_teksti = " ⛔" if t["alle_moq"] else ""
        ax.set_title(f"#{i+1} {t['toimittaja']}\n{t['maa']} · {t['pisteet']}p{moq_teksti}",
                     size=10, fontweight="bold", color=vari, pad=15)

    # Piilota tyhjät ruudut
    for j in range(n_toimittajat, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle(f"Toimittajavertailu — {qty} kpl | {profiili_nimi.title()}",
                 size=16, fontweight="bold", y=1.02)
    plt.tight_layout()

    radar_polku = output_dir / "radar_chart.png"
    plt.savefig(radar_polku, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  {GREEN}✓{RESET} Radar chart: {radar_polku}")

    # ── Volyymikäyrä ──
    fig, ax = plt.subplots(figsize=(12, 7))

    volyymit = list(range(100, 10001, 100))

    for i, t in enumerate(tulokset):
        landed_per_vol = []
        for v in volyymit:
            tulos = laske_landed_cost(t, v)
            landed_per_vol.append(tulos["landed_per_kpl"])
        ax.plot(volyymit, landed_per_vol, linewidth=2, label=t["toimittaja"], color=värit[i])

        # MOQ-merkki
        if t["moq"] >= 100:
            moq_tulos = laske_landed_cost(t, t["moq"])
            ax.axvline(x=t["moq"], color=värit[i], linestyle=":", alpha=0.3)
            ax.plot(t["moq"], moq_tulos["landed_per_kpl"], "o", color=värit[i], markersize=5)

    ax.set_xlabel("Kappalemäärä", fontsize=12)
    ax.set_ylabel("Landed cost / kpl (€)", fontsize=12)
    ax.set_title(f"Volyymi-optimointikäyrä — Landed cost per kappale", fontsize=14)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    volyymi_polku = output_dir / "volyymi_kayra.png"
    plt.savefig(volyymi_polku, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  {GREEN}✓{RESET} Volyymikäyrä: {volyymi_polku}")
    print()


# ──────────────────────────────────────────────
# KERROS 5: CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Toimittajavertailu — Landed Cost Calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esimerkit:
  %(prog)s examples/pihaharavat.csv --qty 1000
  %(prog)s examples/pihaharavat.csv --qty 1000 --profile laatukriittinen
  %(prog)s examples/pihaharavat.csv --qty 1000 --incoterms CIF
  %(prog)s examples/pihaharavat.csv --qty 1000 --override "Ningbo Garden Co:DDP" "Mumbai Garden Pvt:FOB"
        """,
    )

    parser.add_argument("csv", help="Polku toimittaja-CSV-tiedostoon")
    parser.add_argument("--qty", type=int, required=True, help="Tilausmäärä (kpl)")
    parser.add_argument(
        "--profile",
        choices=PROFIILIT.keys(),
        default="tasapainoinen",
        help="Painotusprofiili (oletus: tasapainoinen)",
    )
    parser.add_argument(
        "--incoterms",
        choices=INCOTERMS_SELITE.keys(),
        default=None,
        help="Pakota kaikille toimittajille sama Incoterms-ehto",
    )
    parser.add_argument(
        "--override",
        nargs="+",
        metavar="NIMI:EHTO",
        help='Vaihda yksittäisen toimittajan Incoterms, esim. "Ningbo Garden Co:DDP"',
    )
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Älä luo kuvaajia (ohita matplotlib)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Kansio kuvaajille (oletus: nykyinen kansio)",
    )

    args = parser.parse_args()

    # Parsitaan override-mapit
    overrides = {}
    if args.override:
        for o in args.override:
            if ":" not in o:
                print(f"Virheellinen override-muoto: '{o}'. Käytä muotoa 'Toimittajan nimi:EHTO'", file=sys.stderr)
                sys.exit(1)
            nimi, ehto = o.rsplit(":", 1)
            ehto = ehto.strip().upper()
            if ehto not in INCOTERMS_SELITE:
                print(f"Tuntematon Incoterms: '{ehto}'. Tuetut: {', '.join(INCOTERMS_SELITE.keys())}", file=sys.stderr)
                sys.exit(1)
            overrides[nimi.strip()] = ehto

    # Lue data
    toimittajat = lue_csv(args.csv)

    if not toimittajat:
        print("CSV on tyhjä — ei toimittajia.", file=sys.stderr)
        sys.exit(1)

    # Laske landed cost jokaiselle
    tulokset = []
    for t in toimittajat:
        # Prioriteetti: yksittäinen override > globaali incoterms > CSV:n arvo
        ic_override = overrides.get(t["toimittaja"]) or args.incoterms or None
        tulos = laske_landed_cost(t, args.qty, incoterms_override=ic_override)
        tulokset.append(tulos)

    # Pisteytä
    tulokset = pisteyta(tulokset, args.profile)

    # Tulosta
    tulosta_ranking(tulokset, args.qty, args.profile)
    tulosta_incoterms_vertailu(tulokset, args.qty)
    tulosta_maariskit(tulokset)

    # Kuvaajat
    if not args.no_charts:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        luo_kuvaajat(tulokset, args.qty, args.profile, output_dir)


if __name__ == "__main__":
    main()
