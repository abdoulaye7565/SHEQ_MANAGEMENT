from __future__ import annotations

import unittest

from app.models import Alert, AppUser, Employee, Formation, PresenceRecord


class EmployeeModelTest(unittest.TestCase):
    def _sample_row(self) -> dict:
        return {
            "id_employe": 1,
            "nom": "Diallo",
            "prenom": "Ibrahim",
            "nom_complet": "Diallo Ibrahim",
            "type_employe": "national",
            "site_id": 2,
            "site": "Mine principale",
            "groupe": "Equipe A",
            "fonction": "Superviseur HSE",
            "shift_code": "DAY",
            "statut": "actif",
            "numero_badge": "B-0042",
        }

    def test_from_row_maps_all_fields(self) -> None:
        emp = Employee.from_row(self._sample_row())
        self.assertEqual(emp.id_employe, 1)
        self.assertEqual(emp.nom, "Diallo")
        self.assertEqual(emp.prenom, "Ibrahim")
        self.assertEqual(emp.site, "Mine principale")
        self.assertEqual(emp.numero_badge, "B-0042")

    def test_display_name_nom_prenom(self) -> None:
        emp = Employee.from_row(self._sample_row())
        self.assertEqual(emp.display_name, "Diallo Ibrahim")

    def test_display_name_falls_back_to_nom_complet(self) -> None:
        row = self._sample_row()
        row["nom"] = ""
        row["prenom"] = ""
        emp = Employee.from_row(row)
        self.assertEqual(emp.display_name, "Diallo Ibrahim")

    def test_asdict_returns_all_keys(self) -> None:
        emp = Employee.from_row(self._sample_row())
        d = emp.asdict()
        self.assertIn("id_employe", d)
        self.assertIn("site", d)
        self.assertIn("numero_badge", d)

    def test_none_optional_fields_default_to_empty(self) -> None:
        row = self._sample_row()
        row["groupe"] = None
        row["numero_badge"] = None
        emp = Employee.from_row(row)
        self.assertEqual(emp.groupe, "")
        self.assertEqual(emp.numero_badge, "")


class AlertModelTest(unittest.TestCase):
    def _sample_row(self) -> dict:
        return {
            "alert_id": "ppe:12:Stock bas",
            "source_key": "ppe",
            "source": "EPI et stock",
            "type_alerte": "Stock bas",
            "message": "Gants nitrile - Stock 0 / seuil 2.",
            "niveau": "haut",
            "statut": "ouverte",
            "date_creation": "2026-06-17",
            "reference_id": 12,
            "reference_label": "Gants nitrile",
            "action_hint": "Traiter dans le module EPI",
        }

    def test_from_row_maps_all_fields(self) -> None:
        alert = Alert.from_row(self._sample_row())
        self.assertEqual(alert.alert_id, "ppe:12:Stock bas")
        self.assertEqual(alert.source_key, "ppe")
        self.assertEqual(alert.niveau, "haut")
        self.assertEqual(alert.reference_id, 12)

    def test_asdict_roundtrip(self) -> None:
        alert = Alert.from_row(self._sample_row())
        d = alert.asdict()
        self.assertEqual(d["alert_id"], alert.alert_id)
        self.assertEqual(d["statut"], "ouverte")

    def test_none_reference_id_allowed(self) -> None:
        row = self._sample_row()
        row["reference_id"] = None
        alert = Alert.from_row(row)
        self.assertIsNone(alert.reference_id)


class PresenceRecordModelTest(unittest.TestCase):
    def _sample_row(self) -> dict:
        return {
            "id_presence": 100,
            "employe_id": 5,
            "date_presence": "2026-06-17",
            "statut_presence": "present",
            "heure_entree": "06:00",
            "heure_sortie": "14:00",
            "heures_travaillees": 8.0,
            "shift_id": 1,
        }

    def test_from_row_maps_all_fields(self) -> None:
        rec = PresenceRecord.from_row(self._sample_row())
        self.assertEqual(rec.id_presence, 100)
        self.assertEqual(rec.statut_presence, "present")
        self.assertEqual(rec.heures_travaillees, 8.0)
        self.assertEqual(rec.heure_entree, "06:00")

    def test_none_heures_travaillees(self) -> None:
        row = self._sample_row()
        row["heures_travaillees"] = None
        rec = PresenceRecord.from_row(row)
        self.assertIsNone(rec.heures_travaillees)


class FormationModelTest(unittest.TestCase):
    def _sample_row(self) -> dict:
        return {
            "id_formation": 7,
            "employe_id": 3,
            "type_formation_id": 2,
            "type_formation": "Secourisme",
            "date_formation": "2024-01-15",
            "date_expiration": "2026-01-15",
            "statut": "valide",
            "organisme": "Croix Rouge",
            "score": 85.5,
        }

    def test_from_row_maps_all_fields(self) -> None:
        f = Formation.from_row(self._sample_row())
        self.assertEqual(f.id_formation, 7)
        self.assertEqual(f.type_formation, "Secourisme")
        self.assertEqual(f.score, 85.5)

    def test_none_expiration_allowed(self) -> None:
        row = self._sample_row()
        row["date_expiration"] = None
        f = Formation.from_row(row)
        self.assertIsNone(f.date_expiration)


class AppUserModelTest(unittest.TestCase):
    def _sample_row(self) -> dict:
        return {
            "id_user": 1,
            "username": "admin",
            "role": "Administrateur",
            "statut": "actif",
        }

    def test_from_row_with_modules(self) -> None:
        modules = ["Dashboard", "Admin", "Settings"]
        user = AppUser.from_row(self._sample_row(), modules=modules)
        self.assertEqual(user.username, "admin")
        self.assertEqual(user.modules, modules)

    def test_can_access_checks_module(self) -> None:
        user = AppUser.from_row(self._sample_row(), modules=["Dashboard", "Admin"])
        self.assertTrue(user.can_access("Dashboard"))
        self.assertFalse(user.can_access("Settings"))

    def test_empty_modules_by_default(self) -> None:
        user = AppUser.from_row(self._sample_row())
        self.assertEqual(user.modules, [])
        self.assertFalse(user.can_access("Admin"))


if __name__ == "__main__":
    unittest.main()
