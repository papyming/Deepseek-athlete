# ============================================================
# FICHIER: src/planificateur/plan_intervals.py
# RÔLE: Export du plan vers Intervals.ICU et récupération
#       des retours pour ajustement dynamique
# ============================================================

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .export_csv import exporter_plan_csv
from .export_pdf_plan import exporter_pdf_plan


class IntervalsPlanManager:
    """
    Gestionnaire d'export/récupération avec Intervals.ICU.
    """

    def __init__(self, api_key: str = None, athlete_id: str = None):
        self.api_key = api_key or os.getenv('INTERVALS_API_KEY', '')
        self.athlete_id = athlete_id or os.getenv('INTERVALS_ATHLETE_ID', '')
        self.base_url = 'https://app.intervals.icu/api/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

    # ============================================================
    # 1. EXPORT DU PLAN DE BASE VERS INTERVALS
    # ============================================================

    def exporter_plan_de_base(self, plan: Dict, plan_dir: str) -> Dict:
        """
        Exporte le plan de base :
        - PDF (pour l'athlète)
        - CSV (pour Intervals.ICU)
        - Upload vers Intervals.ICU via API
        """
        print("\n   📤 Export du plan de base vers Intervals.ICU...")

        # 1.1 Exporter CSV et PDF locaux
        csv_path = exporter_plan_csv(plan, plan_dir)
        pdf_path = exporter_pdf_plan(plan, plan_dir)

        # 1.2 Upload vers Intervals.ICU
        resultat = self._upload_plan_intervals(plan)

        # 1.3 Générer un résumé pour l'athlète
        resume = self._generer_resume_plan(plan)

        return {
            'csv_path': csv_path,
            'pdf_path': pdf_path,
            'intervals_result': resultat,
            'resume': resume,
            'plan_modifie': False
        }

    def _upload_plan_intervals(self, plan: Dict) -> Dict:
        """
        Upload le plan vers Intervals.ICU.
        Crée les événements sur les dates du plan.
        """
        resultat = {
            'succes': False,
            'evenements_crees': 0,
            'erreurs': []
        }

        athlete_info = self._get_athlete_info()
        if not athlete_info:
            resultat['erreurs'].append("Impossible de récupérer les infos de l'athlète")
            return resultat

        for semaine in plan.get('semaines', []):
            for jour in semaine.get('jours', []):
                date_str = jour.get('date')
                if not date_str:
                    continue

                for seance in jour.get('seances', []):
                    if seance.get('discipline') in ['Repos', 'Course']:
                        continue

                    # Créer l'événement
                    event_data = self._construire_evenement(seance, date_str)
                    try:
                        response = requests.post(
                            f"{self.base_url}/athlete/{self.athlete_id}/plan/event",
                            headers=self.headers,
                            json=event_data
                        )
                        if response.status_code in [200, 201]:
                            resultat['evenements_crees'] += 1
                        else:
                            resultat['erreurs'].append(
                                f"Erreur {response.status_code} pour {date_str}: {response.text[:100]}"
                            )
                    except Exception as e:
                        resultat['erreurs'].append(f"Exception: {str(e)}")

        resultat['succes'] = resultat['evenements_crees'] > 0
        return resultat

    def _construire_evenement(self, seance: Dict, date_str: str) -> Dict:
        """Construit un événement Intervals.ICU à partir d'une séance."""
        titre_map = {
            'CAP': '🏃 Course à pied',
            'Vélo': '🚴 Cyclisme',
            'Natation': '🏊 Natation',
            'Renforcement': '🏋️ Renforcement'
        }

        discipline = seance.get('discipline', '')
        type_seance = seance.get('type', '')
        duree = seance.get('duree', 45)
        details = seance.get('details', '')

        # Construire le titre
        titre = f"{titre_map.get(discipline, discipline)} - {type_seance}"

        return {
            'date': date_str,
            'title': titre,
            'description': details,
            'duration': duree * 60,  # Intervals attend des secondes
            'plannedRpe': self._estimer_rpe_planifie(seance),
            'tags': [discipline, type_seance]
        }

    def _estimer_rpe_planifie(self, seance: Dict) -> int:
        """Estime le RPE planifié (échelle 1-10 Intervals)."""
        difficulte_map = {
            'recuperation': 2,
            'endurance': 3,
            'seuil': 6,
            'intense': 8,
            'course': 9
        }
        difficulte = seance.get('difficulte', 'endurance')
        rpe = difficulte_map.get(difficulte, 4)
        # Intervals utilise RPE 1-10
        return rpe

    def _get_athlete_info(self) -> Optional[Dict]:
        """Récupère les informations de l'athlète."""
        try:
            response = requests.get(
                f"{self.base_url}/athlete/{self.athlete_id}",
                headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return None

    def _generer_resume_plan(self, plan: Dict) -> Dict:
        """Génère un résumé du plan pour l'athlète."""
        nb_semaines = plan.get('nb_semaines', 0)
        date_debut = plan.get('date_debut', '')
        date_objectif = plan.get('date_objectif', '')

        # Compter les séances par discipline
        disciplines = {}
        for semaine in plan.get('semaines', []):
            for jour in semaine.get('jours', []):
                for seance in jour.get('seances', []):
                    disc = seance.get('discipline', '')
                    if disc not in ['Repos', 'Course']:
                        disciplines[disc] = disciplines.get(disc, 0) + 1

        return {
            'nb_semaines': nb_semaines,
            'date_debut': date_debut,
            'date_objectif': date_objectif,
            'disciplines': disciplines,
            'total_seances': sum(disciplines.values())
        }

    # ============================================================
    # 2. RÉCUPÉRATION DES RETOURS DEPUIS INTERVALS
    # ============================================================

    def recuperer_retours(self, start_date: str = None, end_date: str = None) -> Dict:
        """
        Récupère les retours de l'athlète depuis Intervals.ICU.
        """
        print("\n   📥 Récupération des retours depuis Intervals.ICU...")

        resultat = {
            'retours': [],
            'wellness': [],
            'metrics': {},
            'periode': {'debut': start_date, 'fin': end_date}
        }

        # 2.1 Récupérer les données de bien-être (RPE, FC repos, HRV, poids)
        wellness_data = self._get_wellness(start_date, end_date)
        resultat['wellness'] = wellness_data

        # 2.2 Récupérer les activités (séances réalisées)
        activities_data = self._get_activities(start_date, end_date)
        resultat['retours'] = self._extraire_retours_activites(activities_data)

        # 2.3 Récupérer les métriques de charge (CTL, ATL, TSB)
        resultat['metrics'] = self._get_metrics(start_date, end_date)

        print(f"   ✅ {len(resultat['retours'])} retours récupérés")
        return resultat

    def _get_wellness(self, start_date: str, end_date: str) -> List[Dict]:
        """Récupère les données de bien-être."""
        try:
            params = {}
            if start_date:
                params['from'] = start_date
            if end_date:
                params['to'] = end_date

            response = requests.get(
                f"{self.base_url}/athlete/{self.athlete_id}/wellness",
                headers=self.headers,
                params=params
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

    def _get_activities(self, start_date: str, end_date: str) -> List[Dict]:
        """Récupère les activités réalisées."""
        try:
            params = {}
            if start_date:
                params['from'] = start_date
            if end_date:
                params['to'] = end_date

            response = requests.get(
                f"{self.base_url}/athlete/{self.athlete_id}/activities",
                headers=self.headers,
                params=params
            )
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
        return []

    def _extraire_retours_activites(self, activities: List[Dict]) -> List[Dict]:
        """Extrait les retours (RPE, commentaires) des activités."""
        retours = []
        for act in activities:
            retours.append({
                'date': act.get('date'),
                'rpe': act.get('rpe'),  # 1-10
                'commentaire': act.get('notes', ''),
                'duree_reelle': act.get('duration', 0),  # secondes
                'distance': act.get('distance', 0),
                'titre': act.get('title', '')
            })
        return retours

    def _get_metrics(self, start_date: str, end_date: str) -> Dict:
        """Récupère CTL, ATL, TSB depuis Intervals.ICU."""
        metrics = {'ctl': 0, 'atl': 0, 'tsb': 0}

        try:
            wellness = self._get_wellness(start_date, end_date)
            if wellness:
                # Prendre les dernières valeurs disponibles
                last = wellness[-1] if wellness else {}
                metrics['ctl'] = last.get('ctl', 0)
                metrics['atl'] = last.get('atl', 0)
                metrics['tsb'] = last.get('tsb', 0)
        except Exception:
            pass

        return metrics

    # ============================================================
    # 3. AJUSTEMENT DU PLAN (Option 2 modifiée)
    # ============================================================

    def ajuster_plan_depuis_retours(self, plan: Dict, retours: Dict) -> Dict:
        """
        Ajuste le plan en fonction des retours de l'athlète.
        """
        print("\n   🔄 Ajustement du plan basé sur les retours...")

        modifications = 0
        semaines_ajustees = []

        metrics = retours.get('metrics', {})
        tsb = metrics.get('tsb', 0)

        # Déterminer le niveau d'ajustement
        if tsb < -40:
            niveau = 'critique'
            message = f"TSB très bas ({tsb:.1f}) → Remplacer séances intenses par récupération"
        elif tsb < -25:
            niveau = 'eleve'
            message = f"TSB bas ({tsb:.1f}) → Réduire volume et intensité de 25-30%"
        elif tsb < -10:
            niveau = 'modere'
            message = f"TSB modéré ({tsb:.1f}) → Maintenir avec vigilance"
        else:
            niveau = 'bon'
            message = f"TSB bon ({tsb:.1f}) → Maintenir ou intensifier"

        # Appliquer les ajustements sur les semaines à venir
        for idx, semaine in enumerate(plan.get('semaines', [])):
            # Ne pas ajuster les semaines passées
            date_debut = semaine.get('date_debut')
            if date_debut and datetime.strptime(date_debut, '%Y-%m-%d') < datetime.now():
                continue

            if niveau in ['critique', 'eleve']:
                for jour in semaine.get('jours', []):
                    for seance in jour.get('seances', []):
                        if seance.get('difficulte') in ['intense', 'seuil']:
                            if niveau == 'critique':
                                # Remplacer par récupération
                                seance['discipline'] = seance.get('discipline', 'CAP')
                                seance['type'] = 'Récupération active'
                                seance['details'] = f"Récupération active (remplace séance intense) - TSB={tsb:.1f}"
                                seance['duree'] = max(20, int(seance.get('duree', 30) * 0.5))
                                seance['difficulte'] = 'recuperation'
                                seance['adaptation'] = f"TSB={tsb:.1f} → remplacement"
                            else:
                                # Réduire de 30%
                                duree = seance.get('duree', 0)
                                seance['duree'] = int(duree * 0.7)
                                seance['details'] = f"{seance.get('details', '')} (allégé - TSB={tsb:.1f})"
                                seance['adaptation'] = f"TSB={tsb:.1f} → -30%"
                            modifications += 1
                semaines_ajustees.append(idx + 1)

        return {
            'modifications': modifications,
            'niveau': niveau,
            'message': message,
            'semaines_ajustees': semaines_ajustees,
            'tsb': tsb,
            'plan_modifie': modifications > 0
        }

    # ============================================================
    # 4. EXPORT PDF DU PLAN AJUSTÉ
    # ============================================================

    def exporter_pdf_plan_ajuste(self, plan: Dict, plan_dir: str, ajustements: Dict) -> str:
        """
        Exporte un PDF avec le plan ajusté et les modifications.
        """
        print("\n   📄 Génération du PDF du plan ajusté...")

        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.units import mm

        from export.sov import ajouter_filigrane_pdf

        styles = getSampleStyleSheet()

        titre_style = ParagraphStyle(
            'Titre', parent=styles['Heading1'],
            fontSize=16, alignment=TA_CENTER, spaceAfter=12
        )
        sous_titre_style = ParagraphStyle(
            'SousTitre', parent=styles['Heading2'],
            fontSize=12, spaceAfter=6
        )
        normal_style = styles['Normal']
        alerte_style = ParagraphStyle(
            'Alerte', parent=styles['Normal'],
            fontSize=10, textColor=colors.red, spaceAfter=6
        )
        ok_style = ParagraphStyle(
            'Ok', parent=styles['Normal'],
            fontSize=10, textColor=colors.green, spaceAfter=6
        )

        story = []

        # Titre
        story.append(Paragraph(
            f"Plan d'entraînement ajusté : {plan.get('athlete', 'Inconnu')}",
            titre_style
        ))
        story.append(Spacer(1, 6))

        # Résumé des ajustements
        story.append(Paragraph("Résumé des ajustements", sous_titre_style))

        if ajustements.get('modifications', 0) > 0:
            story.append(Paragraph(
                f"🔧 {ajustements['modifications']} séances ajustées",
                alerte_style
            ))
            story.append(Paragraph(
                f"📊 TSB = {ajustements.get('tsb', 0):.1f}",
                normal_style
            ))
            story.append(Paragraph(
                f"📝 {ajustements.get('message', '')}",
                normal_style
            ))
            if ajustements.get('semaines_ajustees'):
                story.append(Paragraph(
                    f"Semaines concernées : S-{', S-'.join([str(s) for s in ajustements['semaines_ajustees']])}",
                    normal_style
                ))
        else:
            story.append(Paragraph(
                "✅ Aucun ajustement nécessaire, le plan est maintenu",
                ok_style
            ))

        story.append(Spacer(1, 6))

        # Tableau des séances (une semaine au hasard)
        semaines = plan.get('semaines', [])
        if semaines:
            semaine_choisie = semaines[0] if len(semaines) > 0 else None

            if semaine_choisie:
                story.append(Paragraph(
                    f"Aperçu de la semaine du {semaine_choisie.get('date_debut', '')} au {semaine_choisie.get('date_fin', '')}",
                    sous_titre_style
                ))

                data = [
                    [Paragraph("Jour", normal_style),
                     Paragraph("Discipline", normal_style),
                     Paragraph("Type", normal_style),
                     Paragraph("Détails", normal_style),
                     Paragraph("Durée", normal_style),
                     Paragraph("Adaptation", normal_style)]
                ]

                for jour in semaine_choisie.get('jours', []):
                    for seance in jour.get('seances', []):
                        if seance.get('discipline') == 'Repos':
                            continue
                        adaptation = seance.get('adaptation', '')
                        data.append([
                            Paragraph(jour.get('jour', ''), normal_style),
                            Paragraph(seance.get('discipline', ''), normal_style),
                            Paragraph(seance.get('type', ''), normal_style),
                            Paragraph(seance.get('details', '')[:40] + "..." if len(seance.get('details', '')) > 40 else seance.get('details', ''), normal_style),
                            Paragraph(f"{seance.get('duree', 0)} min", normal_style),
                            Paragraph(adaptation, alerte_style if adaptation else normal_style)
                        ])

                table = Table(data, colWidths=[25*mm, 30*mm, 30*mm, 45*mm, 25*mm, 35*mm])
                table.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                    ('FONTSIZE', (0,0), (-1,-1), 8),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('WORDWRAP', (0,0), (-1,-1), True),
                ]))
                story.append(table)

        # Sauvegarde
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nom = plan.get('athlete', 'athlete').replace(' ', '_')
        nom_fichier = f"{nom}_plan_ajuste_{timestamp}.pdf"
        chemin = os.path.join(plan_dir, nom_fichier)

        try:
            doc = SimpleDocTemplate(chemin, pagesize=landscape(A4))
            doc.onFirstPage = ajouter_filigrane_pdf
            doc.onLaterPages = ajouter_filigrane_pdf
            doc.build(story)
            print(f"   📄 PDF ajusté exporté : {chemin}")
            return chemin
        except Exception as e:
            print(f"   ❌ Erreur PDF : {e}")
            return ""

    # ============================================================
    # 5. CYCLE COMPLET : Plan de base → Retours → Ajustement
    # ============================================================

    def cycle_complet(
        self,
        athlete_dir: str,
        plan: Dict,
        plan_dir: str,
        start_date: str = None,
        end_date: str = None
    ) -> Dict:
        """
        Cycle complet :
        1. Export du plan de base vers Intervals
        2. Récupération des retours
        3. Ajustement du plan
        4. Export du PDF ajusté
        """
        print("\n" + "="*60)
        print("🔄 CYCLE PLANIFICATEUR → INTERVALS → AJUSTEMENT")
        print("="*60)

        # Étape 1 : Export du plan de base
        export_result = self.exporter_plan_de_base(plan, plan_dir)

        # Étape 2 : Récupération des retours
        retours = self.recuperer_retours(start_date, end_date)

        # Étape 3 : Ajustement du plan
        ajustements = self.ajuster_plan_depuis_retours(plan, retours)

        # Étape 4 : Export du PDF ajusté
        if ajustements.get('modifications', 0) > 0:
            pdf_ajuste = self.exporter_pdf_plan_ajuste(plan, plan_dir, ajustements)
        else:
            pdf_ajuste = None

        # Résumé
        resultat = {
            'export': export_result,
            'retours': retours,
            'ajustements': ajustements,
            'pdf_ajuste': pdf_ajuste,
            'plan_modifie': ajustements.get('plan_modifie', False)
        }

        print("\n" + "="*60)
        print("📊 RÉSUMÉ DU CYCLE")
        print("="*60)
        print(f"   📤 Événements créés dans Intervals : {export_result.get('intervals_result', {}).get('evenements_crees', 0)}")
        print(f"   📥 Retours récupérés : {len(retours.get('retours', []))}")
        print(f"   🔧 Séances ajustées : {ajustements.get('modifications', 0)}")
        if pdf_ajuste:
            print(f"   📄 PDF ajusté : {os.path.basename(pdf_ajuste)}")
        print("="*60)

        return resultat