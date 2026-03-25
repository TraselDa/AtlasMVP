"""
Génération directe des PDFs de test via fpdf2 (sans dépendance Word).
3 PDFs par catégorie (30 au total).
"""

import os
from fpdf import FPDF
from fpdf.enums import XPos, YPos

BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "documents")

# ── Palette / layout ──────────────────────────────────────────────
HEADER_BG   = (30, 60, 114)   # bleu marine
HEADER_FG   = (255, 255, 255)
LINE_BG     = (240, 244, 250)
TABLE_BORDER = (180, 190, 210)
BODY_COLOR  = (40, 40, 40)

def _sanitize(text):
    """Replace non-latin-1 characters with ASCII equivalents."""
    text = (text
        .replace("\u2013", "-").replace("\u2014", "-")
        .replace("\u2019", "'").replace("\u2018", "'")
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u00e9", "e").replace("\u00e8", "e").replace("\u00ea", "e").replace("\u00eb", "e")
        .replace("\u00e0", "a").replace("\u00e2", "a").replace("\u00e4", "a")
        .replace("\u00ee", "i").replace("\u00ef", "i")
        .replace("\u00f4", "o").replace("\u00f6", "o")
        .replace("\u00f9", "u").replace("\u00fb", "u").replace("\u00fc", "u")
        .replace("\u00e7", "c").replace("\u00c7", "C")
        .replace("\u00c9", "E").replace("\u00c8", "E").replace("\u00ca", "E")
        .replace("\u00c0", "A").replace("\u00c2", "A")
        .replace("\u00d4", "O").replace("\u00d9", "U").replace("\u00db", "U")
        .replace("\u20ac", "EUR").replace("\u00a0", " ")
        .replace("\u2026", "...").replace("\u00ab", "<<").replace("\u00bb", ">>")
        .replace("\u2192", "->").replace("\u2190", "<-").replace("\u2022", "-")
        .replace("\u00b0", " deg").replace("\u00b2", "2").replace("\u00b3", "3")
        .replace("\u00bd", "1/2").replace("\u00d7", "x").replace("\u00f7", "/")
        .replace("\u2248", "~").replace("\u2260", "!=").replace("\u2264", "<=").replace("\u2265", ">=")
        .replace("\u00ae", "(R)").replace("\u00a9", "(c)").replace("\u2122", "(TM)")
    )
    # Fallback: drop any remaining non-latin-1 character
    result = ""
    for ch in text:
        try:
            ch.encode("latin-1")
            result += ch
        except UnicodeEncodeError:
            result += "?"
    return result

class SafePDF(FPDF):
    def cell(self, *args, **kwargs):
        if args:
            args = list(args)
            if len(args) > 2 and isinstance(args[2], str):
                args[2] = _sanitize(args[2])
            args = tuple(args)
        if "text" in kwargs:
            kwargs["text"] = _sanitize(kwargs["text"])
        return super().cell(*args, **kwargs)

    def multi_cell(self, *args, **kwargs):
        if args:
            args = list(args)
            if len(args) > 2 and isinstance(args[2], str):
                args[2] = _sanitize(args[2])
            args = tuple(args)
        if "text" in kwargs:
            kwargs["text"] = _sanitize(kwargs["text"])
        return super().multi_cell(*args, **kwargs)

def _pdf(title_line1, title_line2, ref, org):
    pdf = SafePDF()
    pdf.add_page()
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=20)

    # En-tete colore
    pdf.set_fill_color(*HEADER_BG)
    pdf.rect(0, 0, 210, 28, "F")
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*HEADER_FG)
    pdf.set_xy(18, 6)
    pdf.cell(0, 8, _sanitize(org), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(18)
    pdf.cell(0, 5, f"{_sanitize(title_line1)} - {_sanitize(title_line2)}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_text_color(*BODY_COLOR)
    pdf.set_xy(18, 32)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, f"Réf. : {ref}   |   Date : 25/03/2025", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    return pdf

def h1(pdf, text):
    pdf.set_fill_color(*HEADER_BG)
    pdf.set_text_color(*HEADER_FG)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, f"  {_sanitize(text)}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(*BODY_COLOR)
    pdf.ln(1)

def body(pdf, text, size=9):
    pdf.set_font("Helvetica", "", size)
    pdf.multi_cell(0, 5, _sanitize(str(text)))
    pdf.ln(2)

def table(pdf, headers, rows, col_widths=None):
    w = 174
    n = len(headers)
    if col_widths is None:
        col_widths = [w / n] * n

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(*HEADER_BG)
    pdf.set_text_color(*HEADER_FG)
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 7, f" {h}", border=0, fill=True)
    pdf.ln()

    pdf.set_text_color(*BODY_COLOR)
    fill = False
    for row in rows:
        pdf.set_fill_color(*LINE_BG) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.set_font("Helvetica", "", 8)
        for i, cell in enumerate(row):
            pdf.cell(col_widths[i], 6, f" {cell}", border=0, fill=True)
        pdf.ln()
        fill = not fill
    pdf.ln(3)

def sig_block(pdf, a_name, a_func, a_org, b_name, b_func, b_org):
    pdf.ln(4)
    body(pdf, "Fait à Paris, le 25/03/2025")
    pdf.set_font("Helvetica", "", 8)
    half = 87
    y = pdf.get_y()
    pdf.set_xy(18, y)
    pdf.multi_cell(half, 5,
        f"Pour {a_org}\nSignature : _______________\nNom : {a_name}\nFonction : {a_func}")
    pdf.set_xy(18 + half, y)
    pdf.multi_cell(half, 5,
        f"Pour {b_org}\nSignature : _______________\nNom : {b_name}\nFonction : {b_func}")

# ─────────────────────────────────────────────────────────────────
# CONTRATS (3)
# ─────────────────────────────────────────────────────────────────

def gen_contrat_pdf(idx, ref, objet, ht, prestataire, client, rep_c, rep_p):
    tva = round(ht * 0.20, 2)
    ttc = round(ht + tva, 2)
    pdf = _pdf("CONTRAT DE PRESTATION DE SERVICES", objet, ref, client)

    h1(pdf, "ENTRE LES SOUSSIGNÉS")
    body(pdf,
        f"CLIENT : {client}, représenté par {rep_c}, dont le siège est au 14 rue du Faubourg "
        f"Saint-Antoine, 75011 Paris – SIREN 512 348 901.\n\n"
        f"PRESTATAIRE : {prestataire}, représenté par {rep_p}, dont le siège est au "
        f"7 avenue des Gobelins, 75013 Paris – SIREN 439 812 567.")

    h1(pdf, "ARTICLE 1 – OBJET")
    body(pdf, f"Le présent contrat a pour objet la réalisation de prestations de services portant sur : {objet}.")

    h1(pdf, "ARTICLE 2 – DURÉE")
    body(pdf, "Le contrat prend effet le 25/03/2025 pour une durée de 3 mois, renouvelable par accord exprès.")

    h1(pdf, "ARTICLE 3 – RÉMUNÉRATION")
    table(pdf,
        ["Désignation", "Montant HT", "TVA 20 %", "Montant TTC"],
        [[objet[:45], f"{ht:,.2f} €", f"{tva:,.2f} €", f"{ttc:,.2f} €"]],
        [80, 32, 30, 32])
    body(pdf,
        "30 % à la signature : " + f"{round(ht*0.30):,.2f} € – 70 % à la livraison validée.\n"
        "Paiement par virement sous 30 jours date de facture.\n"
        f"IBAN : FR76 3000 6000 0112 3456 7890 189 – BIC : AGRIFRPP")

    h1(pdf, "ARTICLE 4 – CONFIDENTIALITÉ")
    body(pdf, "Chaque partie s'engage à la confidentialité pour une durée de 5 ans après expiration du contrat.")

    h1(pdf, "ARTICLE 5 – PROPRIÉTÉ INTELLECTUELLE")
    body(pdf, f"Les livrables seront la propriété exclusive de {client} après paiement intégral.")

    h1(pdf, "ARTICLE 6 – RÉSILIATION")
    body(pdf, "Résiliation possible avec 15 jours de préavis en cas de manquement grave non corrigé.")

    h1(pdf, "ARTICLE 7 – LOI APPLICABLE")
    body(pdf, "Droit français applicable. Tribunal de Commerce de Paris compétent.")

    sig_block(pdf, rep_c, "Directeur Général", client, rep_p, "Gérant", prestataire)
    path = os.path.join(BASE_DIR, "contrats", f"contrat_prestation_{idx:03d}.pdf")
    pdf.output(path)
    return path

CONTRATS_PDF = [
    ("CONT-PREST-2024-001", "Développement plateforme e-commerce", 48000,
     "Altimum Consulting SARL", "Nexoria Solutions SAS", "Martin Dupont", "Sophie Laurent"),
    ("CONT-PREST-2024-002", "Audit de sécurité informatique", 12500,
     "Veridis Audit & Finance SARL", "Terralpha SAS", "Isabelle Moreau", "Pierre Girard"),
    ("CONT-PREST-2024-003", "Mission de conseil en stratégie digitale", 30000,
     "Deltaform Groupe SAS", "Oryon Technologies SA", "Thomas Renard", "Alexandre Mercier"),
]

# ─────────────────────────────────────────────────────────────────
# BAUX (3)
# ─────────────────────────────────────────────────────────────────

def gen_bail_pdf(idx, ref, titre, adresse, surface, loyer, depot, bailleur, preneur, rep_b, rep_p):
    pdf = _pdf("CONTRAT DE BAIL", titre, ref, bailleur)

    h1(pdf, "PARTIES")
    body(pdf,
        f"BAILLEUR : {bailleur}, représenté par {rep_b}.\n"
        f"PRENEUR : {preneur}, représenté par {rep_p}.")

    h1(pdf, "ARTICLE 1 – DÉSIGNATION DES LOCAUX")
    body(pdf, f"Locaux situés au {adresse} – Surface : {surface}.")

    h1(pdf, "ARTICLE 2 – DURÉE")
    body(pdf, "Bail consenti pour une durée déterminée à compter du 01/04/2025.")

    h1(pdf, "ARTICLE 3 – LOYER ET CHARGES")
    table(pdf,
        ["Loyer mensuel HT", "Charges/mois", "Dépôt de garantie", "Règlement"],
        [[f"{loyer:,} €", f"{round(loyer*0.12):,} €", f"{depot:,} €", "Virement – 1er du mois"]],
        [44, 34, 48, 48])

    h1(pdf, "ARTICLE 4 – DESTINATION")
    body(pdf, f"Les locaux sont destinés à l'activité de {preneur}. Toute modification d'usage requiert l'accord écrit du bailleur.")

    h1(pdf, "ARTICLE 5 – ÉTAT DES LIEUX")
    body(pdf, "État des lieux contradictoire établi lors de la remise des clés et annexé au présent bail.")

    h1(pdf, "ARTICLE 6 – ASSURANCES")
    body(pdf, "Le preneur doit souscrire une assurance multirisque et en justifier annuellement.")

    sig_block(pdf, rep_b, "Propriétaire / Bailleur", bailleur, rep_p, "Représentant légal", preneur)
    path = os.path.join(BASE_DIR, "baux", f"bail_{idx:03d}.pdf")
    pdf.output(path)
    return path

BAUX_PDF = [
    ("BAIL-COM-2024-001", "Bail commercial – Local 75 m²",
     "8 rue du Temple, 75004 Paris", "75 m²", 1800, 5400,
     "Groupe Lumière & Associés SA", "Nexoria Solutions SAS", "Karim Benali", "Martin Dupont"),
    ("BAIL-RES-2024-001", "Bail d'habitation – Appartement T3 68 m²",
     "12 avenue Victor Hugo, 75016 Paris", "68 m²", 950, 1900,
     "Prismédia Communication SA", "Nathalie Petit", "Céline Fontaine", "Nathalie Petit"),
    ("BAIL-PRO-2024-001", "Bail professionnel – Bureau 45 m²",
     "23 rue de Rivoli, 75001 Paris", "45 m²", 1200, 2400,
     "Apexline Industrie SAS", "Terralpha SAS", "Amandine Leroy", "Isabelle Moreau"),
]

# ─────────────────────────────────────────────────────────────────
# FACTURES (3)
# ─────────────────────────────────────────────────────────────────

def gen_facture_pdf(idx, num, objet, ht, fournisseur, f_siret, f_iban, client, c_siret):
    tva = round(ht * 0.20, 2)
    ttc = round(ht + tva, 2)
    pdf = _pdf("FACTURE", num, num, fournisseur)

    # Bloc coordonnées
    pdf.set_font("Helvetica", "B", 9)
    half = 87
    y = pdf.get_y()
    pdf.set_xy(18, y)
    pdf.multi_cell(half, 5,
        f"ÉMETTEUR :\n{fournisseur}\nSIRET : {f_siret}\n"
        f"14 rue du Faubourg Saint-Antoine, 75011 Paris\n"
        f"Tél : 01 42 58 33 10\ncontact@fournisseur.fr")
    pdf.set_xy(18 + half, y)
    pdf.multi_cell(half, 5,
        f"CLIENT :\n{client}\nSIRET : {c_siret}\n"
        f"7 avenue des Gobelins, 75013 Paris")
    pdf.ln(4)

    body(pdf,
        f"Date d'émission : 25/03/2025   |   Échéance : 24/04/2025\n"
        f"Conditions : 30 jours net – virement bancaire")

    h1(pdf, "DÉTAIL DE LA PRESTATION")
    table(pdf,
        ["Description", "Qté", "P.U. HT", "TVA", "Total HT"],
        [[objet[:50], "1", f"{ht:,.2f} €", "20 %", f"{ht:,.2f} €"]],
        [80, 12, 30, 20, 32])

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Total HT : {ht:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f"TVA (20 %) : {tva:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"TOTAL TTC : {ttc:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 8)
    body(pdf,
        f"Règlement par virement :\nIBAN : {f_iban}\nBIC : AGRIFRPP – Crédit Agricole\n"
        f"Référence à indiquer : {num}\n\n"
        "Pénalités de retard : 3× le taux légal. Indemnité forfaitaire de recouvrement : 40 €.")

    path = os.path.join(BASE_DIR, "factures", f"facture_{idx:03d}.pdf")
    pdf.output(path)
    return path

FACTURES_PDF = [
    ("FAC-2024-0001", "Développement site web e-commerce – Phase 1", 18500,
     "Nexoria Solutions SAS", "512 348 901 00023", "FR76 3000 6000 0112 3456 7890 189",
     "Altimum Consulting SARL", "439 812 567 00041"),
    ("FAC-2024-0002", "Formation Cybersécurité – 2 jours – 8 participants", 3200,
     "Veridis Audit & Finance SARL", "710 345 987 00039", "FR76 1466 7000 0100 1234 5678 901",
     "Terralpha SAS", "621 047 335 00012"),
    ("FAC-2024-0003", "Licences Microsoft 365 Business Premium – 20 postes", 4500,
     "Oryon Technologies SA", "552 148 774 00034", "FR76 3000 4000 0300 0503 8920 147",
     "Deltaform Groupe SAS", "487 659 201 00027"),
]

# ─────────────────────────────────────────────────────────────────
# RAPPORTS FINANCIERS (3)
# ─────────────────────────────────────────────────────────────────

def gen_rapport_pdf(idx, ref, titre, org, daf, pdg, ca, charges, ebit, total_actif, cap_propres):
    result_net = round(ebit * 0.75)
    pdf = _pdf("RAPPORT FINANCIER", titre, ref, org)

    body(pdf,
        f"Préparé par : {daf}, Directeur(rice) Financier(e)\n"
        f"Approuvé par : {pdg}, Président-Directeur Général\n"
        f"Diffusion : {date_str()}")

    h1(pdf, "1. SYNTHÈSE EXÉCUTIVE")
    table(pdf,
        ["Indicateur", "Valeur", "Commentaire"],
        [
            ["Chiffre d'affaires", f"{ca:,} €", "100 %"],
            ["Charges d'exploitation", f"{charges:,} €", f"{round(charges/ca*100,1)} % du CA"],
            ["Résultat d'exploitation (EBIT)", f"{ebit:,} €", f"{round(ebit/ca*100,1)} % du CA"],
            ["Résultat net", f"{result_net:,} €", f"{round(result_net/ca*100,1)} % du CA"],
        ], [70, 50, 54])

    h1(pdf, "2. COMPTE DE RÉSULTAT SIMPLIFIÉ")
    rows_cr = [
        ["Produits d'exploitation", f"{ca:,} €", "100,0 %"],
        ["Achats et charges externes", f"-{round(charges*0.55):,} €", f"-{round(charges*0.55/ca*100,1)} %"],
        ["Frais de personnel", f"-{round(charges*0.35):,} €", f"-{round(charges*0.35/ca*100,1)} %"],
        ["Amortissements", f"-{round(charges*0.10):,} €", f"-{round(charges*0.10/ca*100,1)} %"],
        ["EBIT", f"{ebit:,} €", f"{round(ebit/ca*100,1)} %"],
        ["Impôt sur les sociétés (25 %)", f"-{round(ebit*0.92*0.25):,} €", ""],
        ["Résultat net", f"{result_net:,} €", f"{round(result_net/ca*100,1)} %"],
    ]
    table(pdf, ["Rubrique", "Montant (€)", "% CA"], rows_cr, [90, 50, 34])

    h1(pdf, "3. BILAN SIMPLIFIÉ")
    immo = round(total_actif * 0.40)
    stocks = round(total_actif * 0.10)
    creances = round(total_actif * 0.25)
    dispo = total_actif - immo - stocks - creances
    dettes_fin = round(total_actif * 0.30)
    dettes_fourn = round(total_actif * 0.15)
    autres = max(total_actif - cap_propres - dettes_fin - dettes_fourn, 0)
    table(pdf, ["ACTIF", "Montant (€)", "PASSIF", "Montant (€)"],
        [
            ["Immobilisations nettes", f"{immo:,}", "Capitaux propres", f"{cap_propres:,}"],
            ["Stocks", f"{stocks:,}", "Dettes financières", f"{dettes_fin:,}"],
            ["Créances clients", f"{creances:,}", "Dettes fournisseurs", f"{dettes_fourn:,}"],
            ["Disponibilités", f"{dispo:,}", "Autres dettes", f"{autres:,}"],
            ["TOTAL ACTIF", f"{total_actif:,}", "TOTAL PASSIF", f"{total_actif:,}"],
        ], [44, 43, 44, 43])

    h1(pdf, "4. FLUX DE TRÉSORERIE")
    flux_op = round(ebit + charges * 0.10)
    flux_inv = round(-total_actif * 0.05)
    flux_fin = round(-dettes_fin * 0.08)
    table(pdf, ["Type de flux", "Montant (€)"],
        [
            ["Flux opérationnels", f"+{flux_op:,}"],
            ["Flux d'investissement", f"{flux_inv:,}"],
            ["Flux de financement", f"{flux_fin:,}"],
            ["VARIATION NETTE DE TRÉSORERIE", f"{flux_op+flux_inv+flux_fin:,}"],
        ], [100, 74])

    h1(pdf, "5. COMMENTAIRES")
    perf = "favorable" if ebit > 0 else "défavorable"
    body(pdf,
        f"La direction de {org} note une évolution {perf} de la performance opérationnelle. "
        f"La marge d'exploitation de {round(ebit/ca*100,1)} % est "
        f"{'supérieure' if ebit/ca > 0.05 else 'inférieure'} à l'objectif de 5,0 % fixé en début d'exercice.\n\n"
        "Priorités : optimisation des charges externes, accélération du recouvrement client, "
        "suivi des investissements stratégiques.")

    path = os.path.join(BASE_DIR, "rapports_financiers", f"rapport_financier_{idx:03d}.pdf")
    pdf.output(path)
    return path

from datetime import datetime
def date_str(): return datetime.now().strftime("%d/%m/%Y")

RAPPORTS_PDF = [
    ("RAP-FIN-2023-ANNUEL", "Rapport financier annuel 2023",
     "Nexoria Solutions SAS", "Sophie Laurent", "Martin Dupont",
     12450000, 11820000, 630000, 8500000, 3200000),
    ("RAP-FIN-2024-T1", "Rapport financier T1 2024",
     "Oryon Technologies SA", "Pierre Girard", "Thomas Renard",
     3200000, 2980000, 220000, 12000000, 4800000),
    ("RAP-AUDIT-2024", "Rapport d'audit interne 2024",
     "Altimum Consulting SARL", "Karim Benali", "Sophie Laurent",
     13200000, 12100000, 1100000, 9500000, 4100000),
]

# ─────────────────────────────────────────────────────────────────
# COURRIERS (3)
# ─────────────────────────────────────────────────────────────────

def gen_courrier_pdf(idx, ref, sujet, exped_nom, exped_poste, exped_org, dest_nom, dest_poste, dest_org, intro, corps, conclusion):
    pdf = _pdf("COURRIER ADMINISTRATIF", sujet[:50], ref, exped_org)

    # Bloc coordonnées
    pdf.set_font("Helvetica", "", 8)
    pdf.set_xy(120, 38)
    pdf.multi_cell(72, 4.5,
        f"{exped_nom}\n{exped_poste}\n{exped_org}\n"
        f"14 rue du Faubourg Saint-Antoine\n75011 Paris\n{date_str()}")
    pdf.set_y(max(pdf.get_y(), 68))
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 8)
    body(pdf, f"À l'attention de :\n{dest_nom}\n{dest_poste}\n{dest_org}\n7 avenue des Gobelins, 75013 Paris")
    body(pdf, f"Réf. : {ref}\nObjet : {sujet}")
    body(pdf, "Madame, Monsieur,")
    body(pdf, intro)
    body(pdf, corps)
    body(pdf, conclusion)
    body(pdf,
        "Dans l'attente de votre retour, nous vous prions d'agréer, Madame, Monsieur, "
        "l'expression de nos salutations distinguées.")
    pdf.ln(4)
    body(pdf, f"{exped_nom}\n{exped_poste}\n{exped_org}")

    path = os.path.join(BASE_DIR, "courriers_administratifs", f"courrier_{idx:03d}.pdf")
    pdf.output(path)
    return path

COURRIERS_PDF = [
    ("COUR-2024-001", "Demande de subvention – Programme Innovation Numérique 2024",
     "Martin Dupont", "Directeur Général", "Nexoria Solutions SAS",
     "Sophie Laurent", "Directrice Financière", "Altimum Consulting SARL",
     "Dans le cadre du Programme National d'Innovation Numérique 2024, notre organisation "
     "souhaite soumettre sa candidature pour l'obtention d'une subvention de 85 000 € "
     "destinée au développement d'un outil de gestion documentaire basé sur l'IA.",
     "Notre dossier complet (plan de financement, indicateurs de performance, équipe projet) "
     "est joint en annexe. Le projet créera 4 emplois directs et bénéficiera à 50 PME partenaires.",
     "Nous restons à votre entière disposition pour tout entretien ou complément d'information."),
    ("COUR-2024-004", "Notification de résiliation – Contrat CONT-PREST-2023-018",
     "Karim Benali", "Directeur des Opérations", "Groupe Lumière & Associés SA",
     "Isabelle Moreau", "Responsable Juridique", "Terralpha SAS",
     "Par la présente, nous vous notifions notre décision de mettre fin au contrat de prestation "
     "n°CONT-PREST-2023-018, conformément à l'article 6 prévoyant un préavis de 30 jours.",
     "Cette résiliation prendra effet le 30/04/2025. Nous vous remercions d'assurer la transmission "
     "des livrables en cours et la restitution de tous les éléments appartenant à notre organisation. "
     "Un décompte des prestations réalisées vous sera adressé séparément sous 8 jours.",
     "Nous vous remercions de la qualité de votre collaboration et vous souhaitons bonne continuation."),
    ("COUR-2024-006", "Mise en demeure de règlement – Facture FAC-2024-0234",
     "Nathalie Petit", "Directrice Commerciale", "Novéa Services SARL",
     "Thomas Renard", "Président", "Oryon Technologies SA",
     "Malgré nos relances du 15 et 28 octobre 2024, la facture n°FAC-2024-0234 d'un montant "
     "de 9 750 € TTC, émise le 01/09/2024 et échue le 01/10/2024, demeure impayée.",
     "Nous vous mettons en demeure de régler intégralement cette somme sous 8 jours. "
     "À défaut, nous engagerons une procédure de recouvrement judiciaire. Des pénalités "
     "de retard au taux de 3× le taux légal seront également réclamées.",
     "Cette démarche est le dernier recours amiable avant action en justice."),
]

# ─────────────────────────────────────────────────────────────────
# PV (3)
# ─────────────────────────────────────────────────────────────────

def gen_pv_pdf(idx, ref, titre, org, president, secretaire, participants, points):
    pdf = _pdf("PROCÈS-VERBAL", titre, ref, org)

    body(pdf,
        f"Date : 25/03/2025  |  Heure : 09h30 – 12h00\n"
        f"Lieu : Salle de réunion principale – Siège {org}\n"
        f"Présidé par : {president}")

    h1(pdf, "PARTICIPANTS")
    body(pdf, "Présents :\n" + "\n".join(f"  – {p}" for p in participants))
    body(pdf, f"Secrétaire de séance : {secretaire}")

    h1(pdf, "ORDRE DU JOUR")
    body(pdf, "1. Approbation du PV de la séance précédente\n" +
         "\n".join(f"{i+2}. {pt[0]}" for i, pt in enumerate(points)) +
         f"\n{len(points)+2}. Questions diverses")

    h1(pdf, "DÉROULEMENT")
    body(pdf, "1. Approbation du PV précédent : adopté à l'unanimité.")
    for i, (sujet, cr, decision) in enumerate(points, 2):
        h1(pdf, f"{i}. {sujet}")
        body(pdf, cr)
        pdf.set_font("Helvetica", "B", 8)
        pdf.multi_cell(0, 5, f">> Decision : {_sanitize(decision)}")
        pdf.set_font("Helvetica", "", 9)
        pdf.ln(2)

    body(pdf, f"Questions diverses : aucune.\nSéance levée à 12h00 par {president}.")

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 8)
    half = 87
    y = pdf.get_y()
    pdf.set_xy(18, y)
    pdf.multi_cell(half, 5, f"Président(e) de séance\n{president}\nSignature : _______________")
    pdf.set_xy(18 + half, y)
    pdf.multi_cell(half, 5, f"Secrétaire de séance\n{secretaire}\nSignature : _______________")

    path = os.path.join(BASE_DIR, "proces_verbaux", f"pv_{idx:03d}.pdf")
    pdf.output(path)
    return path

PV_PDF = [
    ("PV-CA-2024-001", "Conseil d'Administration – 15 janvier 2024",
     "Nexoria Solutions SAS", "Martin Dupont", "Sophie Laurent",
     ["Karim Benali – Dir. Opérations", "Isabelle Moreau – Resp. Juridique",
      "Thomas Renard – Dir. Technique", "Nathalie Petit – Dir. Commerciale"],
     [("Approbation des comptes 2023",
       "Les comptes présentent un résultat net de 850 000 €. Bilan total : 8,5 M€. Trésorerie nette : +1,2 M€.",
       "APPROUVÉ à l'unanimité."),
      ("Affectation du résultat",
       "Proposition d'affecter 200 K€ en réserves légales et 650 K€ en report à nouveau.",
       "DÉCIDÉ à l'unanimité.")]),
    ("PV-AGO-2024-001", "Assemblée Générale Ordinaire – 28 mars 2024",
     "Oryon Technologies SA", "Thomas Renard", "Pierre Girard",
     ["Amandine Leroy – Présidente", "Alexandre Mercier – DRH",
      "Céline Fontaine – Dir. Générale", "Martin Dupont – Invité"],
     [("Comptes sociaux 2023 – CA : 25,6 M€ – RN : 1,8 M€",
       "Les comptes sociaux présentés par la direction sont conformes aux normes comptables françaises. Commissaires aux comptes : rapport sans réserve.",
       "ADOPTÉ à l'unanimité (100 % des voix)."),
      ("Renouvellement mandat CAC",
       "Le mandat du cabinet Ernst & Young est renouvelé pour 6 exercices.",
       "RENOUVELÉ à l'unanimité.")]),
    ("PV-CODIR-2024-001", "Comité de Direction – 8 février 2024",
     "Groupe Lumière & Associés SA", "Karim Benali", "Sophie Laurent",
     ["Martin Dupont – DG", "Isabelle Moreau – Resp. Juridique",
      "Nathalie Petit – Dir. Commerciale", "Thomas Renard – Dir. Technique"],
     [("Résultats T4 2023 et plan 2024",
       "CA T4 : 3,2 M€ en hausse de 8 % vs T4 2022. Objectif 2024 fixé à 14 M€ avec marge cible 10,5 %.",
       "OBJECTIF 2024 validé. Plan commercial Q1 approuvé."),
      ("Recrutements prioritaires Q1",
       "DRH propose 4 recrutements : 2 dev senior (60K€), 1 chef projet (55K€), 1 analyste BI (45K€).",
       "BUDGET RECRUTEMENT approuvé : 220 000 € annuels chargés.")]),
]

# ─────────────────────────────────────────────────────────────────
# BONS DE COMMANDE (3)
# ─────────────────────────────────────────────────────────────────

def gen_bdc_pdf(idx, num, objet, ht, qte, acheteur, fournisseur, responsable, approbateur):
    tva = round(ht * 0.20, 2)
    ttc = round(ht + tva, 2)
    pu = round(ht / max(qte, 1), 2)

    pdf = _pdf("BON DE COMMANDE", num, num, acheteur)

    pdf.set_font("Helvetica", "", 8)
    half = 87
    y = pdf.get_y()
    pdf.set_xy(18, y)
    pdf.multi_cell(half, 4.5,
        f"ACHETEUR :\n{acheteur}\nResponsable : {responsable}\n"
        f"Date : 25/03/2025\nLivraison souhaitée : 08/04/2025")
    pdf.set_xy(18 + half, y)
    pdf.multi_cell(half, 4.5,
        f"FOURNISSEUR :\n{fournisseur}\n"
        f"Tél : 01 53 79 44 20\ncontact@fournisseur.fr")
    pdf.ln(4)

    h1(pdf, "DÉTAIL DE LA COMMANDE")
    table(pdf,
        ["Réf.", "Désignation", "Qté", "P.U. HT", "TVA", "Total HT"],
        [[f"REF-{num[-4:]}", objet[:38], str(qte), f"{pu:,.2f} €", "20 %", f"{ht:,.2f} €"]],
        [20, 70, 12, 28, 16, 28])

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Total HT : {ht:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f"TVA (20 %) : {tva:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"TOTAL TTC : {ttc:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 8)
    body(pdf,
        f"Livraison : {acheteur} – 14 rue du Faubourg Saint-Antoine, 75011 Paris\n"
        f"Contact livraison : {responsable}\n"
        f"Conditions de paiement : 30 jours net – virement")
    body(pdf, f"Approuvé par : {approbateur}\nDate : 25/03/2025\nSignature : _______________")

    path = os.path.join(BASE_DIR, "bons_de_commande", f"bdc_{idx:03d}.pdf")
    pdf.output(path)
    return path

BDC_PDF = [
    ("BDC-2024-0001", "Matériel informatique – 10 postes HP EliteBook 840 G10", 15600, 10,
     "Nexoria Solutions SAS", "Oryon Technologies SA", "Martin Dupont", "Sophie Laurent"),
    ("BDC-2024-0002", "Mobilier de bureau – Tables et chaises Salle Réunion A", 4200, 1,
     "Altimum Consulting SARL", "Deltaform Groupe SAS", "Karim Benali", "Sophie Laurent"),
    ("BDC-2024-0004", "Licences Microsoft 365 Business Premium – 20 postes", 3600, 20,
     "Terralpha SAS", "Apexline Industrie SAS", "Isabelle Moreau", "Karim Benali"),
]

# ─────────────────────────────────────────────────────────────────
# BULLETINS DE SALAIRE (3)
# ─────────────────────────────────────────────────────────────────

def gen_bulletin_pdf(idx, num, periode, employe, adresse, brut, poste, matricule, iban):
    ss = round(brut * 0.069, 2)
    ret = round(brut * 0.0315, 2)
    cho = round(brut * 0.024, 2)
    mut = round(brut * 0.015, 2)
    csg = round(brut * 0.068, 2)
    crds = round(brut * 0.029, 2)
    total_sal = round(ss + ret + cho + mut + csg + crds, 2)
    net = round(brut - total_sal, 2)
    pas = round((brut - total_sal + crds) * 0.08, 2)
    net_final = round(net - pas, 2)
    cout_emp = round(brut * 1.45, 2)

    pdf = _pdf("BULLETIN DE PAIE", periode, num, "Nexoria Solutions SAS")

    pdf.set_font("Helvetica", "", 8)
    half = 87
    y = pdf.get_y()
    pdf.set_xy(18, y)
    pdf.multi_cell(half, 4.5,
        "EMPLOYEUR :\nNexoria Solutions SAS\n14 rue du Faubourg Saint-Antoine\n"
        "75011 Paris\nSIRET : 512 348 901 00023\nCCN : SYNTEC (IDCC 1486)")
    pdf.set_xy(18 + half, y)
    pdf.multi_cell(half, 4.5,
        f"EMPLOYÉ(E) :\n{employe}\n{adresse}\n"
        f"Matricule : {matricule}\nPoste : {poste}\nEntrée : 01/03/2022")
    pdf.ln(3)

    h1(pdf, "ÉLÉMENTS DE RÉMUNÉRATION")
    table(pdf,
        ["Rubrique", "Base", "Taux sal.", "Montant"],
        [
            ["Salaire de base", f"{brut:,.2f} €", "–", f"{brut:,.2f} €"],
            ["Cotis. Sécu. sociale", f"{brut:,.2f} €", "6,90 %", f"-{ss:,.2f} €"],
            ["Retraite compl. ARRCO", f"{brut:,.2f} €", "3,15 %", f"-{ret:,.2f} €"],
            ["Assurance chômage", f"{brut:,.2f} €", "2,40 %", f"-{cho:,.2f} €"],
            ["Mutuelle santé", f"{brut:,.2f} €", "1,50 %", f"-{mut:,.2f} €"],
            ["CSG déductible", f"{brut:,.2f} €", "6,80 %", f"-{csg:,.2f} €"],
            ["CSG/CRDS non déd.", f"{brut:,.2f} €", "2,90 %", f"-{crds:,.2f} €"],
        ], [80, 36, 28, 30])

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Salaire brut : {brut:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f"Total cotisations salariales : -{total_sal:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, f"Prélèvement à la source (8 %) : -{pas:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, f"NET À PAYER : {net_final:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, f"Coût total employeur : {cout_emp:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)
    body(pdf, f"Virement effectué le 28/03/2025 – IBAN : {iban}")

    path = os.path.join(BASE_DIR, "bulletins_de_salaire", f"bulletin_{idx:03d}.pdf")
    pdf.output(path)
    return path

BULLETINS_PDF = [
    ("BULL-2024-JAN-001", "janvier 2024", "Lucas Martin", "12 rue des Acacias, 75017 Paris",
     4500, "Développeur Senior", "DEV-2024-042", "FR76 3000 4005 0123 4567 8901 234"),
    ("BULL-2024-FEV-001", "février 2024", "Marie Dubois", "8 avenue Foch, 75116 Paris",
     4200, "Chef de projet", "CP-2024-017", "FR76 1027 8061 0000 0301 2456 789"),
    ("BULL-2024-MAI-001", "mai 2024", "Nicolas Robert", "22 bd Victor Hugo, 92200 Neuilly",
     5500, "Directeur Commercial", "DC-2024-002", "FR76 1025 7020 0100 2345 6789 012"),
]

# ─────────────────────────────────────────────────────────────────
# RELEVÉS BANCAIRES (3)
# ─────────────────────────────────────────────────────────────────

def gen_releve_pdf(idx, num, periode, org, banque, iban, solde_ouv, solde_clo, ops):
    pdf = _pdf("RELEVÉ DE COMPTE", periode.upper(), num, banque)

    body(pdf,
        f"Titulaire : {org}\nIBAN : {iban}\nBIC : AGRIFRPP\n"
        f"Agence : {banque} – Paris Centre")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, f"Solde d'ouverture : {solde_ouv:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    h1(pdf, "OPÉRATIONS DU MOIS")
    table(pdf,
        ["Date", "Libellé", "Débit (€)", "Crédit (€)"],
        [[d, l, f"{db:,.2f}" if db else "", f"{cr:,.2f}" if cr else ""] for d, l, db, cr in ops],
        [20, 90, 32, 32])

    total_deb = sum(o[2] for o in ops if o[2])
    total_cred = sum(o[3] for o in ops if o[3])
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, f"Total débits : {total_deb:,.2f} €   |   Total crédits : {total_cred:,.2f} €",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, f"Solde de clôture : {solde_clo:,.2f} €", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 7)
    body(pdf, "\nEn cas d'anomalie, contacter votre agence sous 30 jours.")

    path = os.path.join(BASE_DIR, "releves_bancaires", f"releve_{idx:03d}.pdf")
    pdf.output(path)
    return path

RELEVES_PDF = [
    ("REL-BNQ-2024-JAN", "janvier 2024", "Nexoria Solutions SAS", "Crédit Agricole",
     "FR76 3000 6000 0112 3456 7890 189", 145800, 182450,
     [("02/01", "VIR ENTRANT – Altimum Consulting SARL", None, 62500),
      ("05/01", "PRELEVEMENT – Loyer bureau Paris 11ème", 2160, None),
      ("08/01", "VIR SORTANT – Oryon Technologies SA", 18200, None),
      ("10/01", "VIR ENTRANT – Terralpha SAS", None, 28000),
      ("12/01", "PRELEVEMENT – URSSAF cotisations", 11664, None),
      ("15/01", "PAIEMENT CB – Fournitures de bureau", 480, None),
      ("18/01", "VIR SORTANT – Salaires janvier 2024", 41200, None),
      ("20/01", "FRAIS BANCAIRES MENSUELS", 180, None),
      ("22/01", "VIR ENTRANT – Remboursement TVA DGFiP", None, 4374),
      ("25/01", "VIR ENTRANT – Deltaform Groupe SAS", None, 45000),
      ("28/01", "VIR SORTANT – Apexline Industrie SAS", 9800, None),
      ("30/01", "VIR SORTANT – Veridis Audit & Finance", 3340, None)]),
    ("REL-BNQ-2024-MAR", "mars 2024", "Terralpha SAS", "BNP Paribas",
     "FR76 1780 6004 0000 1234 5678 910", 167300, 221600,
     [("04/03", "VIR ENTRANT – Nexoria Solutions SAS", None, 75000),
      ("06/03", "PRELEVEMENT – Loyer entrepôt", 4200, None),
      ("09/03", "VIR SORTANT – Fournisseur matières premières", 32000, None),
      ("12/03", "VIR ENTRANT – Oryon Technologies SA", None, 48000),
      ("14/03", "PRELEVEMENT – URSSAF cotisations", 22500, None),
      ("18/03", "VIR SORTANT – Salaires mars 2024", 68000, None),
      ("20/03", "FRAIS BANCAIRES", 220, None),
      ("22/03", "VIR ENTRANT – Remboursement TVA", None, 9800),
      ("25/03", "VIR ENTRANT – Groupe Lumière SA", None, 55000),
      ("28/03", "VIR SORTANT – Prestataires divers", 8980, None)]),
    ("REL-BNQ-2024-SEP", "septembre 2024", "Oryon Technologies SA", "BNP Paribas",
     "FR76 3000 4000 0300 0503 8920 147", 204300, 268700,
     [("02/09", "VIR ENTRANT – Nexoria Solutions SAS", None, 120000),
      ("05/09", "PRELEVEMENT – Loyer La Défense", 8400, None),
      ("08/09", "VIR SORTANT – Altimum Consulting SARL", 45000, None),
      ("10/09", "VIR ENTRANT – Terralpha SAS", None, 85000),
      ("12/09", "PRELEVEMENT – URSSAF + retraites", 48000, None),
      ("15/09", "PAIEMENT CB – Équipements SI", 12500, None),
      ("18/09", "VIR SORTANT – Salaires septembre 2024", 185000, None),
      ("20/09", "FRAIS BANCAIRES", 380, None),
      ("22/09", "VIR ENTRANT – Remboursement TVA DGFiP", None, 18200),
      ("25/09", "VIR ENTRANT – Deltaform Groupe SAS", None, 140000),
      ("28/09", "VIR SORTANT – Prestataires Cloud/Infra", 25400, None)]),
]

# ─────────────────────────────────────────────────────────────────
# CONVENTIONS (3)
# ─────────────────────────────────────────────────────────────────

def gen_convention_pdf(idx, ref, titre, part_a, rep_a, qual_a, part_b, rep_b, qual_b,
                       objet, oblig_a, oblig_b, duree, financier, juridiction):
    pdf = _pdf("CONVENTION", titre, ref, part_a)

    h1(pdf, "PARTIES")
    body(pdf,
        f"Partie A : {part_a}, représentée par {rep_a}, {qual_a}.\n"
        f"Partie B : {part_b}, représentée par {rep_b}, {qual_b}.")

    h1(pdf, "ARTICLE 1 – OBJET")
    body(pdf, objet)

    h1(pdf, "ARTICLE 2 – OBLIGATIONS DES PARTIES")
    body(pdf, f"Partie A : {oblig_a}\n\nPartie B : {oblig_b}")

    h1(pdf, "ARTICLE 3 – DURÉE")
    body(pdf, f"La présente convention est conclue pour : {duree}, à compter du 25/03/2025.")

    h1(pdf, "ARTICLE 4 – CONDITIONS FINANCIÈRES")
    body(pdf, financier)

    h1(pdf, "ARTICLE 5 – CONFIDENTIALITÉ ET RGPD")
    body(pdf,
        "Toute information échangée est strictement confidentielle. Les données personnelles "
        "sont traitées conformément au RGPD (UE) 2016/679 et la loi Informatique et Libertés.")

    h1(pdf, "ARTICLE 6 – RÉSILIATION & DROIT APPLICABLE")
    body(pdf,
        f"Résiliation avec préavis de 30 jours par LRAR. Droit français applicable. "
        f"Juridiction compétente : {juridiction}.")

    sig_block(pdf, rep_a, qual_a, part_a, rep_b, qual_b, part_b)
    path = os.path.join(BASE_DIR, "conventions", f"convention_{idx:03d}.pdf")
    pdf.output(path)
    return path

CONVENTIONS_PDF = [
    ("CONV-PART-2024-001", "Convention de partenariat stratégique",
     "Nexoria Solutions SAS", "Martin Dupont", "Directeur Général",
     "Altimum Consulting SARL", "Sophie Laurent", "Directrice Financière",
     "La présente convention définit les modalités de coopération commerciale en Europe du Sud.",
     "Prospection et avant-vente (min. 5 RDV qualifiés/mois), co-animation d'événements.",
     "Réponse technique, démonstrations, déploiement et support clients.",
     "3 ans renouvelables", "Partage des revenus : 60 % Partie A – 40 % Partie B.",
     "Tribunal de Commerce de Paris"),
    ("CONV-DPA-2024-001", "Convention de traitement de données personnelles (DPA)",
     "Oryon Technologies SA", "Thomas Renard", "Président",
     "Terralpha SAS", "Isabelle Moreau", "Responsable Juridique",
     "Encadrer le traitement des données à caractère personnel échangées conformément au RGPD.",
     "Définir les finalités, base légale, droits des personnes, registre des traitements.",
     "Traiter les données selon les instructions du responsable, notifier tout incident sous 72h.",
     "Durée de la prestation principale",
     "Aucune contrepartie financière – intégré au contrat de service principal.",
     "Tribunal judiciaire de Paris"),
    ("CONV-STAGE-2024-001", "Convention de stage",
     "Groupe Lumière & Associés SA", "Karim Benali", "Directeur des Opérations",
     "Université Paris-Dauphine", "Pr. Anne Lefebvre", "Directrice de l'IUP Finance",
     "Accueil d'un(e) étudiant(e) en stage de fin d'études – Master Finance.",
     "Accueil, encadrement par tuteur désigné, accès aux outils, validation des missions.",
     "Suivi pédagogique, validation des compétences, délivrance du diplôme.",
     "4 mois – du 03/02/2025 au 30/05/2025",
     "Gratification légale : 4,35 €/heure brut (≈ 676 €/mois).",
     "Tribunal de Commerce de Paris"),
]

# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    print("Génération des PDFs...")
    count = 0

    for i, data in enumerate(CONTRATS_PDF, 1):
        p = gen_contrat_pdf(i, *data)
        print(f"  ✓ {os.path.basename(p)}")
        count += 1

    for i, data in enumerate(BAUX_PDF, 1):
        p = gen_bail_pdf(i, *data)
        print(f"  ✓ {os.path.basename(p)}")
        count += 1

    for i, data in enumerate(FACTURES_PDF, 1):
        p = gen_facture_pdf(i, *data)
        print(f"  ✓ {os.path.basename(p)}")
        count += 1

    for i, data in enumerate(RAPPORTS_PDF, 1):
        p = gen_rapport_pdf(i, *data)
        print(f"  ✓ {os.path.basename(p)}")
        count += 1

    for i, data in enumerate(COURRIERS_PDF, 1):
        p = gen_courrier_pdf(i, *data)
        print(f"  ✓ {os.path.basename(p)}")
        count += 1

    for i, data in enumerate(PV_PDF, 1):
        p = gen_pv_pdf(i, *data)
        print(f"  ✓ {os.path.basename(p)}")
        count += 1

    for i, data in enumerate(BDC_PDF, 1):
        p = gen_bdc_pdf(i, *data)
        print(f"  ✓ {os.path.basename(p)}")
        count += 1

    for i, data in enumerate(BULLETINS_PDF, 1):
        p = gen_bulletin_pdf(i, *data)
        print(f"  ✓ {os.path.basename(p)}")
        count += 1

    for i, data in enumerate(RELEVES_PDF, 1):
        p = gen_releve_pdf(i, *data)
        print(f"  ✓ {os.path.basename(p)}")
        count += 1

    for i, data in enumerate(CONVENTIONS_PDF, 1):
        p = gen_convention_pdf(i, *data)
        print(f"  ✓ {os.path.basename(p)}")
        count += 1

    print(f"\n{count} PDFs générés dans {BASE_DIR}")

if __name__ == "__main__":
    main()
